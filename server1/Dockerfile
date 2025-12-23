# 1. Base Image
FROM python:3.13.1-slim

# 2. 시스템 종속성 설치 (pkg-config 및 MySQL 개발 라이브러리)
RUN apt-get update && apt-get install -y \
    pkg-config \
    gcc \
    libmariadb-dev \
    libmariadb-dev-compat \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 종속성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 전체 코드 복사
COPY . .