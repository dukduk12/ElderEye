# src/interface/schema/notification.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationOut(BaseModel):
    id: int
    user_id: int
    notification_type: str   
    serial_number: Optional[str]   
    video_url: Optional[str]   
    event_type: Optional[str]   
    event_time: datetime
    content: str   
    sent_at: datetime
    is_read: bool

    class Config:
        orm_mode = True  
