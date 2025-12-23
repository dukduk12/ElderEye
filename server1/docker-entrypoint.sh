#!/bin/bash

# Alembic 마이그레이션 실행
echo "Running Alembic migrations..."
alembic upgrade head

# FastAPI 서버 실행
echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 9123 --reload
