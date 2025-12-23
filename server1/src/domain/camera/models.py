# src/domain/camera/models.py
# 카메라 관련 테이블 
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Float, LargeBinary
from sqlalchemy.orm import relationship
import pytz
from datetime import datetime

from src.infra.db.database import Base

KST = pytz.timezone('Asia/Seoul')
class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(255), unique=True, nullable=False, index=True)  
    owner_id = Column(Integer, ForeignKey("users.id"))  
    privacy_mode = Column(Boolean, default=False)  
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)  


    latitude = Column(LargeBinary, nullable=True)   
    longitude = Column(LargeBinary, nullable=True)  

    created_at = Column(DateTime, default=lambda: datetime.now(KST))

    owner = relationship("User", back_populates="cameras")  
    camera_settings = relationship("UserCameraSettings", back_populates="camera")
    family_members = relationship("FamilyMember", back_populates="camera")  

class UserCameraSettings(Base):
    __tablename__ = "user_camera_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), index=True)
    is_fixed = Column(Boolean, default=False)
    receive_alarm = Column(Boolean, default=True)
    last_viewed = Column(DateTime, default=None)   
    
    user = relationship("User", back_populates="camera_settings")
    camera = relationship("Camera", back_populates="camera_settings")

class FamilyMember(Base):
    __tablename__ = "family_members"
    
    id = Column(Integer, primary_key=True, index=True)   
    camera_id = Column(Integer, ForeignKey("cameras.id"), index=True)  
    user_id = Column(Integer, ForeignKey("users.id"), index=True)   
    role = Column(Enum("user", "admin", name="role_enum"), default="user")  
    added_at = Column(DateTime, default=datetime.utcnow)   
    status = Column(Enum("pending", "accepted", "rejected", name="status_enum"), default="pending")  

    
    camera = relationship("Camera", back_populates="family_members")
    user = relationship("User", back_populates="family_members")
