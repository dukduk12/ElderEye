# src/infra/email.py
# 이메일 발송 코드
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pydantic_settings import BaseSettings
from datetime import datetime, timedelta
import random
import string

class EmailService(BaseSettings):
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str
    sender_password: str

    class Config:
        env_file = ".env"
        extra = "allow"

    # 1) send email code
    def send_email(self, to_email: str, subject:str, body:str):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, to_email, msg.as_string())
                server.quit()
        except Exception as e:
            print(f"Error sending email: {e}")

    # 2) generate the random auth code
    def generate_auth_code(self, length=6):
        characters = string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
class EmailAuthService:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    # 1) send auth code to email
    def send_auth_code(self, to_email:str):
        auth_code = self.email_service.generate_auth_code()
        subject= "ElderEye 인증 코드 발송"
        body = f"인증 코드: {auth_code}"
        self.email_service.send_email(to_email, subject,body)
        return auth_code
