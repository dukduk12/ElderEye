# src/interface/schema/camera.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CameraRegisterRequest(BaseModel):
    serial_number: str
    privacy_mode: bool = False
    name: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location: str = ""

class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    privacy_mode: Optional[bool] = None
    location: Optional[str] = None

class CameraSettingUpdateRequest(BaseModel):
    is_fixed: Optional[bool] = None
    receive_alarm: Optional[bool] = None

class CameraOut(BaseModel):
    id: int
    serial_number: str
    name: str
    location: str
    privacy_mode: bool
    latitude: float  # 복호화된 위도
    longitude: float  # 복호화된 경도
    created_at: datetime
    is_fixed: bool
    last_viewed: Optional[datetime]
    receive_alarm: bool   
    is_admin: bool

    class Config:
        orm_mode = True

class FamilyAddRequest(BaseModel):
    new_user_id: int

class CameraDeleteRequest(BaseModel):
    camera_id: int

class FamilyMemberStatusRequest(BaseModel):
    serial_number: str   
    action: str

class FamilyMemberOut(BaseModel):
    user_id: int
    nickname: str
    email: str
    role: str

    class Config:
        orm_mode = True