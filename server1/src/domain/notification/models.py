# src/domain/notification/models.py
# 알림 관련 테이블
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import pytz
from datetime import datetime
from src.infra.db.database import Base

KST = pytz.timezone('Asia/Seoul')
class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)   
    user_id = Column(Integer, ForeignKey("users.id"), index=True)   
    notification_type = Column(Enum("family", "emergency", "system", name="notification_type_enum"), nullable=False)  # 알림 유형
    
    serial_number = Column(String(255), nullable=True)
    video_url = Column(String(1024), nullable=True) 
    event_type = Column(String(255), nullable=True) 
    event_time = Column(DateTime, default=lambda: datetime.now(KST))

    content = Column(String(255))  
    sent_at = Column(DateTime, default=lambda: datetime.now(KST))
    is_read = Column(Boolean, default=False)   
    
    user = relationship("User", back_populates="notifications")  
