# src/application/notification/notification.py
# FCM 및 notification 관련 코드
import os
import firebase_admin
from firebase_admin import messaging, credentials

from src.domain.notification.models import Notification
from sqlalchemy.orm import Session

FIREBASE_CRED_PATH = os.getenv("FIREBASE_CREDENTIAL_PATH", "src/infra/firebase/eldereye-ad814-firebase-adminsdk-fbsvc-bfe90d31bf.json")

# 최초 1회만 초기화
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred)

class FCMService:
    @staticmethod
    def send_notification(token: str, event_type: str, content: str, camera_name: str):
        if event_type == "initial_signup":
            title = "ElderEye에 오신걸 환영합니다!"
            body = f"회원가입을 축하합니다, {content}!"
        elif event_type == "fall_detected":
            title = f"🚨알림: 넘어짐이 감지되었습니다."
            body = f"긴급: {camera_name} 카메라에서 넘어짐이 감지되었습니다. ElderEye에 접속해보세요."
        elif event_type == "family_add":
            title = f"새로운 가족이 추가되었습니다."
            body = content 
        elif event_type == "family_add_request":
            title = f"💌새로운 가족 초대가 왔습니다!"
            body = content 
        else:
            title = f"알림: {event_type}"
            body = content 

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token
        )
        try:
            response = messaging.send(message)
            print(f"FCM response: {response}")
            return response
        except Exception as e:
            print(f"Error sending FCM notification: {e}")
            return None

def get_user_notifications(db: Session, user_id: int):
    notifications = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.event_time.desc()).all()
    return notifications