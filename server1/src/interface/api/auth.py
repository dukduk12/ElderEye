# src/interface/api/auth.py
# 회원 가입 관련 api
from fastapi import APIRouter, HTTPException, Body, Depends
from sqlalchemy.orm import Session
from src.application.auth.user_service import create_user
from src.infra.db.database import get_db
from src.application.auth.email_auth import AuthService
from src.application.auth.jwt_auth import login_user
from src.application.auth.jwt_auth import refresh_access_token
from fastapi.security import OAuth2PasswordRequestForm


router = APIRouter()

# 1) Send auth code to user email
@router.post("/send-auth-code/")
async def send_auth_code(email:str = Body(...), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    result = auth_service.generate_and_send_auth_code(email)
    return{"message": result}

# 2) Verfity the email auth code
@router.post("/verify-auth-code/")
async def verify_auth_code(email:str = Body(...), code:str=Body(...), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    is_valid = auth_service.verify_auth_code(email,code)
    if not is_valid:
        print(f"이메일: {email}, 인증 코드: {code}가 유효하지 않습니다.")
        raise HTTPException(status_code=400, detail="유효하지 않거나 만료된 인증 코드입니다")
    return {"message": "인증 코드가 유효합니다"}

# 3) DB에 저장 -> 생성
@router.post("/register/")
async def register_user(email:str = Body(...), nickname: str = Body(...), password:str=Body(...), db: Session = Depends(get_db)):
    try:
        user = create_user(db, email, nickname, password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"message":"회원가입이 완료되었습니다", "user_id" : user.id}

# 4) 로그인
@router.post("/login/")
async def login(email:str = Body(...), password:str = Body(...), device_id:str = Body(...),fcm_token:str=Body(...),db:Session=Depends(get_db)):
    try:
        login_response = login_user(db,email,password,device_id, fcm_token)
    except HTTPException as e:
        raise e
    return login_response

# 5) refresh token
@router.post("/refresh/")
async def refresh_token(
    device_id: str = Body(...), 
    refresh_token: str = Body(...), 
    db: Session = Depends(get_db)
):
    return refresh_access_token(db, device_id, refresh_token)

# 6 ) token 인증용
@router.post("/token", tags=["OAuth2"])
async def oauth2_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return login_user(
        db,
        email=form_data.username,
        password=form_data.password,
        device_id="swagger_device", 
        fcm_token="swagger_fcm"    
    )