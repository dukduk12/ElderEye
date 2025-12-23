# src/application/auth/email_auth.py
# 이메일 인증 서비스 (이메일 보내기 및 인증 코드 검증하기)
from src.infra.email import EmailService, EmailAuthService
from src.infra.db.database import SessionLocal  
from src.domain.user.models import User 
from datetime import datetime, timedelta, timezone

email_service = EmailService()
email_auth_service = EmailAuthService(email_service=email_service)

auth_codes = {}

class AuthService:
    def __init__(self, db: SessionLocal):   # type: ignore
        self.db = db
    
    def get_user_by_email(self, email: str) -> User:
        return self.db.query(User).filter(User.email == email).first()
    
    def generate_and_send_auth_code(self, email: str):
        if self.get_user_by_email(email):
            return "이메일이 이미 등록되어 있습니다."

        auth_code = email_auth_service.send_auth_code(email)

        if not auth_code:
            return "인증 코드를 전송하는데 실패했습니다. 다시 시도해 주세요."
        
        expiration_time = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        email = email.strip().lower()
        auth_codes[email] = {"auth_code": auth_code, "expiration_time": expiration_time}
        
        print(f"Stored auth code for {email}: {auth_code}, expiration time: {expiration_time}")
        print(f"Current auth_codes: {auth_codes}")
        
        return "Auth code has been successfully sent"
    
    def verify_auth_code(self, email: str, code: str):
        email = email.strip().lower()
        print(f"Verifying auth code for {email}...")

        print(f"Current auth_codes: {auth_codes}")
        
        if email not in auth_codes:
            print(f"Auth code for {email} not found.")
            return False
        
        stored_data = auth_codes[email]
        
        if datetime.now(timezone.utc) > stored_data["expiration_time"]:
            print(f"Auth code for {email} has expired.")
            return False
        
        if stored_data["auth_code"] == code:
            print(f"Auth code for {email} is valid.")
            return True
        else:
            print(f"Entered auth code {code} is incorrect for {email}.")
            return False
