# src/infra/redis/redis_subscriber.py
# redis 알림 수신 
import redis
import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from src.infra.db.database import SessionLocal
from src.domain.notification.models import Notification
from src.domain.user.models import UserDevice
from src.domain.camera.models import FamilyMember, Camera, UserCameraSettings
from src.application.notification.notification import FCMService
from typing import Dict
from threading import Thread

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

class RedisSubscriber:
    def __init__(self, redis_host: str, redis_port: int):
        self.redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0)
        self.redis_channel = "event_alert_channel"
        logger.info(f"RedisSubscriber initialized with host={redis_host}, port={redis_port}")

    # 1) listen to the server3 redis event
    def listen_notifications(self):
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(self.redis_channel)

        logger.info("Listening for notifications...")
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    notification_data = json.loads(message["data"])
                    logger.info(f"Received message: {notification_data}")
                    self.save_notification(notification_data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e} - raw message: {message['data']}")

    # 2) Saving to the Center Database
    def save_notification(self, notification_data: Dict):
        db: Session = SessionLocal()
        try:
            serial_number = notification_data.get('serial_number')
            camera = db.query(Camera).filter(Camera.serial_number == serial_number).first()

            if not camera:
                logger.warning(f"Camera with serial number '{serial_number}' not found.")
                return

            users_to_notify_dict = dict()  
            users_to_notify_dict[camera.owner.id] = camera.owner
            logger.info(f"Owner of camera {camera.name} (ID: {camera.id}) added to notification list.")

            family_members = db.query(FamilyMember).filter(FamilyMember.camera_id == camera.id).all()
            for family_member in family_members:
                user_camera_settings = db.query(UserCameraSettings).filter(
                    UserCameraSettings.user_id == family_member.user.id,
                    UserCameraSettings.camera_id == camera.id
                ).first()

                if user_camera_settings and user_camera_settings.receive_alarm:
                    users_to_notify_dict[family_member.user.id] = family_member.user
                    logger.info(f"Family member {family_member.user.id} added to notification list.")

            users_to_notify = list(users_to_notify_dict.values())
            self.send_notification_to_users(users_to_notify, notification_data, camera.name)

            for user in users_to_notify:
                content_message = f"{camera.name}에서 넘어짐을 감지하였습니다"
                notification = Notification(
                    user_id=user.id,
                    notification_type="emergency",
                    serial_number=serial_number,
                    video_url=notification_data.get('video_url'),
                    event_type="fall_detected",
                    content=content_message,
                    sent_at=datetime.utcnow()
                )
                db.add(notification)
                logger.info(f"Notification object created for user {user.id}")

            db.commit()
            logger.info(f"Saved notifications for {len(users_to_notify)} users.")

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving notification: {e}", exc_info=True)
        finally:
            db.close()

    def send_notification_to_users(self, users, notification_data, camera_name):
        for user in users:
            fcm_token = self.get_fcm_token(user)
            if fcm_token:
                logger.info(f"Sending notification to user {user.id}")
                FCMService.send_notification(
                    token=fcm_token,
                    event_type=notification_data.get('event_type', 'fall_detected'),
                    content=notification_data.get('content', 'An emergency has occurred.'),
                    camera_name=camera_name
                )
            else:
                logger.warning(f"No FCM token found for user {user.id}")

    def get_fcm_token(self, user):
        db = SessionLocal()
        try:
            user_device = db.query(UserDevice).filter(UserDevice.user_id == user.id).first()
            return user_device.fcm_token if user_device else None
        except Exception as e:
            logger.error(f"Error fetching FCM token for user {user.id}: {e}", exc_info=True)
            return None
        finally:
            db.close()