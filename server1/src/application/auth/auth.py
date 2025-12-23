# src/application/auth/auth.py
# 모든 API 호출 시 JWT 인증 하는 방법 (라우터 접근 시 헤더에 포함된 Bearer를 읽어 미들웨어적 역할을 함)
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.infra.db.database import get_db
import jwt
from src.domain.user.models import User
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token") 

# JWT에서 사용자의 정보를 얻는 함수
def get_user_from_jwt(token: str, db: Session): # type: ignore
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# 의존성 주입을 통해 JWT 토큰을 확인하는 함수
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)): # type: ignore
    return get_user_from_jwt(token, db)

