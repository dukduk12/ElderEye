# src/domain/user/models.py
# 유저 관련 테이블
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from src.infra.db.database import Base 
from sqlalchemy.orm import relationship
from src.domain.notification.models import Notification

import pytz
from datetime import datetime

KST = pytz.timezone('Asia/Seoul')

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    nickname = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(KST))

    devices = relationship("UserDevice", back_populates='user')
    cameras = relationship("Camera", back_populates="owner")
    family_members = relationship("FamilyMember", back_populates="user")   
    notifications = relationship("Notification", back_populates="user")   
    camera_settings = relationship("UserCameraSettings", back_populates="user")

class UserDevice(Base):
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(String(255), unique=True, index=True)
    fcm_token = Column(String(255))
    refresh_token = Column(String(255))
    
    user = relationship("User", back_populates="devices")