# src/interface/api/notification.py
# 알림 관련 로그
from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from src.domain.notification.models import Notification
from src.application.notification.notification import get_user_notifications
from src.application.auth.auth import get_current_user
from src.infra.db.database import get_db
from src.interface.schema.notification import NotificationOut   
from src.domain.user.models import User

router = APIRouter()

@router.get("/notifications/", response_model=List[NotificationOut])
async def list_user_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notifications = get_user_notifications(db, current_user.id)
    return notifications
