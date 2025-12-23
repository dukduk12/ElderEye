# src/interface/api/camera.py
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session, joinedload
from typing import List
from src.application.camera.camera import register_camera, get_user_cameras, add_family_member_by_user_id, delete_camera, accept_or_reject_family_member,remove_family_member
from src.application.auth.auth import get_current_user
from src.infra.db.database import get_db
from src.domain.user.models import User
from src.domain.camera.models import Camera, FamilyMember,UserCameraSettings
from src.interface.schema.camera import CameraOut, FamilyMemberStatusRequest,CameraRegisterRequest, FamilyAddRequest,  CameraDeleteRequest,  CameraUpdateRequest, CameraSettingUpdateRequest, FamilyMemberOut 
from datetime import datetime
from fastapi import Path
import pytz

KST = pytz.timezone("Asia/Seoul")

router = APIRouter()

# 1) 카메라 등록
@router.post("/cameras/", status_code=status.HTTP_201_CREATED)
async def register_camera_route(
    body: CameraRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_camera = register_camera(
        serial_number=body.serial_number,
        privacy_mode=body.privacy_mode,
        name=body.name,
        latitude=body.latitude,
        longitude=body.longitude,
        location=body.location,
        db=db,
        owner_id=current_user.id
    )
    return {"message": "Camera registered successfully", "camera_id": new_camera.id}

# 2) 등록된 카메라 목록
@router.get("/cameras/", response_model=List[CameraOut])
async def list_user_cameras(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cameras = get_user_cameras(db, current_user.id)   
    return cameras

# 3) 가족 구성원 추가를 위한 닉네임으로 사용자 조회 [only admin]
@router.get("/cameras/find_user", status_code=status.HTTP_200_OK)
async def add_family_member_route(
    nickname: str,   
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    user_to_add = db.query(User).filter(User.nickname == nickname).first()
    
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User with given nickname not found.")

    return {
        "user_id": user_to_add.id,
        "nickname": user_to_add.nickname,
        "email": user_to_add.email  
    }

# 4) 가족 구성원 추가 [only admin who add the camera]
@router.post("/cameras/{camera_id}/family_member", status_code=status.HTTP_200_OK)
async def add_family_member_route(
    camera_id: int,
    body: FamilyAddRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_to_add = db.query(User).filter(User.id == body.new_user_id).first()
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User with given ID not found.")
    
    return add_family_member_by_user_id(camera_id, user_to_add.id, db, current_user.id)

# 5) 카메라 삭제 [only admin]
@router.delete("/cameras/{camera_id}", status_code=status.HTTP_200_OK)
async def delete_camera_route(
    camera_id: int = Path(..., description="ID of the camera to delete"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return delete_camera(camera_id, db, current_user.id)

# 6) 가족 구성원 수락/거절
@router.post("/cameras/family_member", status_code=status.HTTP_200_OK)
async def accept_or_reject_family_member_route(
    body: FamilyMemberStatusRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
 
    camera = db.query(Camera).filter_by(serial_number=body.serial_number).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found with the given serial number.")
 
    return accept_or_reject_family_member(
        camera.id, user_id, body.action, db
    )

# 7) 한놈의 가족 삭제
@router.delete("/cameras/{camera_id}/remove_family/{user_id_to_remove}", status_code=status.HTTP_200_OK)
async def remove_family_member_route(
    camera_id: int, 
    user_id_to_remove: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    result = remove_family_member(camera_id, user_id_to_remove, db, current_user.id)
    return result

# 8) 카메라 정보 수정 [only admin]
@router.patch("/cameras/{camera_id}", status_code=status.HTTP_200_OK)
async def update_camera_route(
    camera_id: int,
    body: CameraUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
): 
    camera = db.query(Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")
     
    if camera.owner_id != current_user.id:
        family_member = db.query(FamilyMember).filter_by(camera_id=camera_id, user_id=current_user.id).first()
        if not family_member or family_member.role != 'admin':
            raise HTTPException(status_code=403, detail="You are not authorized to update this camera.")
     
    if body.name:
        camera.name = body.name
    if body.privacy_mode is not None:
        camera.privacy_mode = body.privacy_mode
    if body.location:
        camera.location = body.location
    
    db.commit()
    db.refresh(camera)
    
    return {"message": "Camera updated successfully", "camera_id": camera.id}

# 9) 사용자 카메라 설정 수정 (토글형 옵션)
@router.patch("/cameras/{camera_id}/settings", status_code=status.HTTP_200_OK)
async def update_user_camera_settings_route(
    camera_id: int,
    body: CameraSettingUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
): 
    setting = db.query(UserCameraSettings).filter_by(camera_id=camera_id, user_id=current_user.id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="User settings for this camera not found.")
     
    if body.is_fixed is not None:
        setting.is_fixed = body.is_fixed
    if body.receive_alarm is not None:
        setting.receive_alarm = body.receive_alarm
    
    db.commit()
    db.refresh(setting)
    
    return {"message": "Camera settings updated successfully"}

# 10) 카메라 스트리밍을 본 후, last_viewed만 업데이트 
@router.patch("/cameras/{camera_id}/last_viewed", status_code=status.HTTP_200_OK)
async def update_last_viewed(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  
    setting = db.query(UserCameraSettings).filter_by(camera_id=camera_id, user_id=current_user.id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="User settings for this camera not found.")
      
    setting.last_viewed = datetime.now(KST)   
    db.commit()
    db.refresh(setting)

    return {"message": "Last viewed updated successfully", "last_viewed": setting.last_viewed}

# 11) camera family member list
@router.get("/cameras/{camera_id}/members", status_code=status.HTTP_200_OK)
async def get_camera_family_members(
    camera_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camera = db.query(Camera).filter_by(id=camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")

    membership = db.query(FamilyMember).filter_by(camera_id=camera_id, user_id=current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="You do not have access to this camera.")

    family_members = (
        db.query(FamilyMember)
        .options(joinedload(FamilyMember.user))
        .filter_by(camera_id=camera_id, status="accepted")
        .all()
    )

    result = []
    for member in family_members:
        result.append({
            "user_id": member.user.id,
            "nickname": member.user.nickname,
            "email": member.user.email,
            "role": member.role
        })

    return result

# 12) serial number to information
@router.get("/cameras/info_by_serial/{serial_number}", status_code=status.HTTP_200_OK)
async def get_camera_info_by_serial(
    serial_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    camera = db.query(Camera).filter_by(serial_number=serial_number).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found.")
    
    # 가족 구성원인지 확인
    family_member = db.query(FamilyMember).filter_by(
        camera_id=camera.id,
        user_id=current_user.id,
        status="accepted"
    ).first()

    if not family_member:
        raise HTTPException(status_code=403, detail="You do not have access to this camera.")
    
    # 설정 정보 가져오기
    setting = db.query(UserCameraSettings).filter_by(
        camera_id=camera.id,
        user_id=current_user.id
    ).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Camera setting not found for this user.")

    return {
        "id": camera.id,
        "name": camera.name,
        "privacy_mode": camera.privacy_mode,
        "is_admin": family_member.role == "admin",
        "receive_alarm": setting.receive_alarm
    }