FROM python:3.10-slim

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    ffmpeg libsm6 libxext6 \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --upgrade pip

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사 및 캐시 가능한 pip 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# 전체 소스 복사
COPY . .

# 포트 노출
EXPOSE 6000

# gRPC 서버 실행
CMD ["python", "app/main.py"]
