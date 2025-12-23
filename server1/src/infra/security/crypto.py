# src/infra/security/crypto.py
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# .env 파일을 로드하여 환경 변수로 설정
load_dotenv()

# 환경 변수에서 ENCRYPTION_KEY 값을 가져오는 함수
def get_key() -> bytes:
    key = os.getenv("ENCRYPTION_KEY")
    if key is None:
        raise ValueError("ENCRYPTION_KEY 환경변수가 설정되지 않았습니다.")
    return key.encode()

# 암호화
def encrypt_coordinates(latitude: float, longitude: float) -> dict:
    key = get_key()  # 환경 변수에서 키를 가져옴
    cipher_suite = Fernet(key)
    
    # latitude와 longitude를 문자열로 변환하여 암호화
    encrypted_latitude = cipher_suite.encrypt(str(latitude).encode())
    encrypted_longitude = cipher_suite.encrypt(str(longitude).encode())
    
    return {
        "latitude": encrypted_latitude,
        "longitude": encrypted_longitude
    }

# 복호화
def decrypt_coordinates(encrypted_latitude: bytes, encrypted_longitude: bytes) -> dict:
    key = get_key()  # 환경 변수에서 키를 가져옴
    cipher_suite = Fernet(key)
    
    # 복호화 후, 문자열을 float으로 변환하여 반환
    decrypted_latitude = cipher_suite.decrypt(encrypted_latitude).decode()
    decrypted_longitude = cipher_suite.decrypt(encrypted_longitude).decode()
    
    return {
        "latitude": float(decrypted_latitude),
        "longitude": float(decrypted_longitude)
    }
