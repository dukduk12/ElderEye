# src/infra/db/db.py
# MySQL과의 연결 설정 (cf) SQLAlchemy 는 ORM
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# .env 에서 MySQL 접속 정보 받기
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL") 

# SQLAlchemy 설정
engine = create_engine(DATABASE_URL, connect_args={'charset':'utf8mb4'}) 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 

Base = declarative_base() # 베이스 클래스 생성성

def get_db():
    logging.debug("Creating a new DB session")
    db=SessionLocal()
    logging.debug(f"Session object created: {db}")
    try: 
        yield db
    finally:
        db.close()

# # DB 연결 확인 함수
# def test_db_connection():
#     try:
#         with engine.connect() as connection:
#             print("✅ DB connect success")
#     except Exception as e:
#         print(f"❌ DB connect fail: {e}")

# if __name__ == "__main__":
#     test_db_connection()
