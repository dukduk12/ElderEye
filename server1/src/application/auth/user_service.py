# src/application/auth/user_service.py
# 회원가입 마무리 로직
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from src.domain.user.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1) hash the password
def hash_password(password:str)->str:
    return pwd_context.hash(password)

# 2) DB 에 저장
def create_user(db : Session, email:str, nickname:str, password:str):
    existing_user = get_user_by_email(db,email)
    if existing_user:
        raise ValueError("이미 등록된 이메일입니다")
    
    hashed_password = hash_password(password)
    db_user = User(email=email, nickname=nickname, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 3) 이메일로 구분?
def get_user_by_email(db:Session,email:str):
    return db.query(User).filter(User.email == email).first()