# src/application/camera/camera.py
# 카메라 등록, 소유자 추가 및 카메라 스트리밍 기타 옵션
from datetime import datetime
from src.domain.user.models import User 
from src.domain.camera.models import Camera, FamilyMember, UserCameraSettings
from src.application.notification.notification import FCMService   
from src.domain.notification.models import Notification
from src.infra.security.crypto import encrypt_coordinates, decrypt_coordinates  
from sqlalchemy.orm import Session,joinedload
from fastapi import HTTPException, status

# 1) 카메라 등록 
def register_camera(serial_number: str, privacy_mode: bool, name: str, latitude: float = None, longitude: float = None, location: str = "", db: Session = None, owner_id: int = None):
    existing_camera = db.query(Camera).filter(Camera.serial_number == serial_number).first()
    if existing_camera:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Camera with this serial number already exists")
    
    encrypted_coordinates = encrypt_coordinates(latitude, longitude)
    
    new_camera = Camera(
        serial_number=serial_number,
        owner_id=owner_id,
        privacy_mode=privacy_mode,
        name=name,
        latitude=encrypted_coordinates["latitude"],   
        longitude=encrypted_coordinates["longitude"],  
        location=location,
    )
    db.add(new_camera)
    db.flush()   

    family_member = FamilyMember(
        camera_id=new_camera.id,
        user_id=owner_id,
        role="admin",
        status="accepted"
    )
    db.add(family_member)

    camera_setting = UserCameraSettings(
        camera_id=new_camera.id,
        user_id=owner_id,
        is_fixed=False,
        receive_alarm=True,
        last_viewed=None
    )
    db.add(camera_setting)

    db.commit()
    db.refresh(new_camera)
    return new_camera

# 2) 카메라 리스트 조회
def get_user_cameras(db: Session, user_id: int): 
    family_roles = db.query(FamilyMember).filter(
        FamilyMember.user_id == user_id
    ).all()

    camera_list = []

    for role in family_roles:
        setting = db.query(UserCameraSettings).options(
            joinedload(UserCameraSettings.camera)
        ).filter(
            UserCameraSettings.user_id == user_id,
            UserCameraSettings.camera_id == role.camera_id
        ).first()

        if setting and setting.camera:
            camera = setting.camera
            decrypted_coordinates = decrypt_coordinates(camera.latitude, camera.longitude)

            camera_data = {
                "id": camera.id,
                "serial_number": camera.serial_number,
                "name": camera.name,
                "location": camera.location,
                "privacy_mode": camera.privacy_mode,
                "latitude": decrypted_coordinates["latitude"],
                "longitude": decrypted_coordinates["longitude"],
                "created_at": camera.created_at,
                "is_fixed": setting.is_fixed,
                "last_viewed": setting.last_viewed,
                "receive_alarm": setting.receive_alarm,
                "is_admin": role.role == "admin"   
            }
            camera_list.append(camera_data)

    return camera_list

# 3) 가족 구성원 추가 [only admin who add the camera]
def add_family_member_by_user_id(camera_id: int, user_id_to_add: int, db: Session, current_user_id: int):
    admin_record = db.query(FamilyMember).filter_by(
        camera_id=camera_id, user_id=current_user_id, role="admin"
    ).first()
    if not admin_record:
        raise HTTPException(status_code=403, detail="You are not authorized to add members to this camera.")
    
    user_to_add = db.query(User).filter(User.id == user_id_to_add).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User with given ID not found.")

    existing_member = db.query(FamilyMember).filter_by(
        camera_id=camera_id, user_id=user_id_to_add
    ).first()
    if existing_member:
        if existing_member.status == "accepted":
            raise HTTPException(status_code=400, detail="This user is already a member of the camera.")
        else:
            raise HTTPException(status_code=400, detail="This user has a pending or rejected request.")

    new_member = FamilyMember(
        camera_id=camera_id,
        user_id=user_id_to_add,
        role="user",
        status="pending"
    )
    db.add(new_member)

    send_fcm_notification(user_to_add, current_user_id, camera_id, db)
    save_notification(user_to_add, current_user_id, camera_id, db)

    db.commit()
    return {"message": f"{user_to_add.nickname} has been added as a family member (pending approval)."}

def send_fcm_notification(user_to_add, current_user_id, camera_id, db: Session):
    user_devices = user_to_add.devices
    if not user_devices:
        print(f"[FCM] No devices found for user_id={user_to_add.id}")
        return
    
    token = user_devices[0].fcm_token
    if not token:
        print(f"[FCM] No FCM token found for user_id={user_to_add.id}")
        return

    user_setting = db.query(UserCameraSettings).filter_by(
        user_id=user_to_add.id, camera_id=camera_id
    ).first()

    if user_setting is not None and user_setting.receive_alarm is False:
        print(f"[FCM] User has explicitly disabled alarm notifications. Skipping FCM.")
        return

    camera = db.query(Camera).filter_by(id=camera_id).first()
    if not camera:
        print(f"[FCM] No camera found with id={camera_id}")
        return
    
    admin_user = db.query(User).filter_by(id=current_user_id).first()
    admin_nickname = admin_user.nickname if admin_user else "Unknown Admin"
    
    fcm_service = FCMService()
    fcm_service.send_notification(
        token,
        event_type="family_add_request",
        content=f"{admin_nickname}님이 {camera.name}에 회원님을 초대했습니다.",
        camera_name=camera.name
    )
    print(f"[FCM] Notification sent to user_id={user_to_add.id}, token={token}")

def save_notification(user_to_add, current_user_id, camera_id, db: Session):
    admin_user = db.query(User).filter_by(id=current_user_id).first()
    if not admin_user:
        raise HTTPException(status_code=404, detail="Admin user not found.")

    camera = db.query(Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")

    notification = Notification(
        user_id=user_to_add.id,
        notification_type="family",
        serial_number=camera.serial_number,
        content=f"새로운 가족 추가 요청이 {camera.name}에서 왔습니다.",
        event_type="family_add_request",
        event_time=datetime.utcnow(),
        is_read=False
    )
    db.add(notification)
    db.commit()

# 4) 카메라 삭제 [only admin who add the camera]
def delete_camera(camera_id: int, db: Session, current_user_id: int):
    camera = db.query(Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")

    if camera.owner_id != current_user_id:
        raise HTTPException(status_code=403, detail="You are not the owner of this camera.")

    db.query(UserCameraSettings).filter_by(camera_id=camera_id).delete()
    db.query(FamilyMember).filter_by(camera_id=camera_id).delete()
    db.delete(camera)
    db.commit()
    return {"message": "Camera deleted successfully."}

# 5) 가족 구성원 수락/거절
def accept_or_reject_family_member(camera_id: int, user_id: int, action: str, db: Session):
    family_member = db.query(FamilyMember).filter_by(camera_id=camera_id, user_id=user_id).first()
    if not family_member:
        raise HTTPException(status_code=404, detail="Family member not found.")
    
    if family_member.status != "pending":
        raise HTTPException(status_code=400, detail="This request has already been processed.")

    admin_user = db.query(User).filter_by(id=family_member.camera.owner_id).first()
    admin_nickname = admin_user.nickname if admin_user else "Unknown Admin"
    
    camera = db.query(Camera).filter_by(id=camera_id).first()
    camera_name = camera.name if camera else "Unknown Camera"  

    if action == "accept":
        family_member.status = "accepted"
         
        camera_setting = UserCameraSettings(
            camera_id=camera_id,
            user_id=user_id,
            is_fixed=False,   
            receive_alarm=True,    
            last_viewed=None
        )
        db.add(camera_setting)
        
        notification_content = f"{family_member.user.nickname}님이 {camera_name}에 가족 구성원으로 추가되었습니다."
    elif action == "reject":
        family_member.status = "rejected"
        notification_content = f"{family_member.user.nickname}님이 {camera_name}에 대한 가족 구성원 요청을 거절했습니다."
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'accept' or 'reject'.")

    family_members = db.query(FamilyMember).filter_by(camera_id=camera_id).all()
    for fm in family_members:
        save_notification_for_accept_or_reject(fm.user_id, notification_content, camera, db)

    db.commit()
    return {"message": f"Family member {action}ed successfully."}

def save_notification_for_accept_or_reject(user_id: int, content: str, camera: Camera, db: Session):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    notification = Notification(
        user_id=user.id,
        notification_type="family",
        content=content,
        event_type="family_add",
        event_time=datetime.utcnow(),
        is_read=False,
        serial_number=camera.serial_number if camera else ""
    )
    db.add(notification)
    db.commit()

# 6) 가족 구성원 삭제 [only admin who add the camera]
def remove_family_member(camera_id: int, user_id_to_remove: int, db: Session, current_user_id: int):
    admin_record = db.query(FamilyMember).filter_by(
        camera_id=camera_id, user_id=current_user_id, role="admin"
    ).first()
    if not admin_record:
        raise HTTPException(status_code=403, detail="You are not authorized to remove members from this camera.")
   
    user_to_remove = db.query(FamilyMember).filter_by(camera_id=camera_id, user_id=user_id_to_remove).first()
    if not user_to_remove:
        raise HTTPException(status_code=404, detail="Family member not found for this camera.")

    db.delete(user_to_remove)
    
    camera = db.query(Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")
    
    family_members = db.query(FamilyMember).filter_by(camera_id=camera_id).all()
    for fm in family_members:
        save_notification_for_accept_or_reject(fm.user_id, f"{user_to_remove.user.nickname}님이 {camera.name}에서 제거되었습니다.", camera, db)
    
    db.commit()
    return {"message": f"Family member {user_to_remove.user.nickname} removed successfully from the camera."}