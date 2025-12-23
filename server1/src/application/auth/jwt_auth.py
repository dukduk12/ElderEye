# src/application/auth/jwt_auth.py
# JWT 토큰 생성 , 검증 및 사용자 로그인 
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, status
from src.domain.user.models import User,UserDevice
from src.infra.db.database import SessionLocal
import os
from fastapi import HTTPException

from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 1) 비밀번호 검증을 위한 패스워드 해시 처리 및 확인
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 2) JWT 토큰 생성
def create_access_token(data: dict, expires_delta: timedelta = None):
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 3) refresh_token 생성
def create_refresh_token(data: dict):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 4) 이메일로 사용자 조회
def get_user_by_email(db: SessionLocal, email: str): # type: ignore
    return db.query(User).filter(User.email == email).first()

# 5) 로그인
def login_user(db: SessionLocal, email: str, password: str,device_id, fcm_token: str): # type: ignore
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    save_device_token(db, user.id, device_id, fcm_token, refresh_token)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# 6) 디바이스에 refresh_token 저장
def save_device_token(db: SessionLocal, user_id: int, device_id: str, fcm_token: str, refresh_token: str): # type: ignore
    # 기존 디바이스가 있으면 refresh_token 갱신
    device = db.query(UserDevice).filter(UserDevice.user_id == user_id, UserDevice.device_id == device_id).first()
    
    if device:
        print(f"[save_device_token] 기존 디바이스 발견. refresh_token 갱신")
        device.refresh_token = refresh_token
        device.fcm_token = fcm_token
        db.commit()
        db.refresh(device)
    else:
        print(f"[save_device_token] 새로운 디바이스 등록")
        new_device = UserDevice(user_id=user_id, device_id=device_id, fcm_token=fcm_token, refresh_token=refresh_token)
        db.add(new_device)
        db.commit()
        db.refresh(new_device)

# 7) refresh token
def refresh_access_token(db: SessionLocal, device_id: str, refresh_token: str):  # type: ignore
    try:
        print(f"[refresh_access_token] device_id={device_id}")
        print(f"[refresh_access_token] refresh_token={refresh_token}")

        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        print(f"[refresh_access_token] decoded email: {email}")
        
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
        user = get_user_by_email(db, email)
        if not user:
            print(f"[refresh_access_token] User not found for email={email}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 🔍 디버깅: 해당 유저의 모든 디바이스 정보 출력
        devices = db.query(UserDevice).filter(UserDevice.user_id == user.id).all()
        for d in devices:
            print(f"[refresh_access_token] registered device: id={d.device_id}, token={d.refresh_token}")

        # 🔎 실제 비교 쿼리 수행
        device = db.query(UserDevice).filter(
            UserDevice.user_id == user.id,
            UserDevice.device_id == device_id,
            UserDevice.refresh_token == refresh_token
        ).first()

        if not device:
            print(f"[refresh_access_token] ❌ 디바이스 또는 토큰이 일치하지 않음")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token or device")
        
        print(f"[refresh_access_token] ✅ 디바이스 확인 완료 - 토큰 재발급 진행")
        new_access_token = create_access_token(data={"sub": user.email})
        new_refresh_token = create_refresh_token(data={"sub": user.email})

        device.refresh_token = new_refresh_token
        db.commit()
        db.refresh(device)

        print(f"[refresh_access_token] 🔁 토큰 갱신 완료: access_token={new_access_token[:30]}..., refresh_token={new_refresh_token[:30]}...")
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except ExpiredSignatureError as e:
        print(f"[refresh_access_token] ❌ 리프레시 토큰 만료: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

    except InvalidTokenError as e:
        print(f"[refresh_access_token] ❌ 토큰 디코딩 실패 (무효한 토큰): {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    except HTTPException as e:
        print(f"[refresh_access_token] ⚠️ HTTPException re-raised: {e.status_code} - {e.detail}")
        raise e

    except Exception as e:
        print(f"[refresh_access_token] 🔥 Unexpected error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
