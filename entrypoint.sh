#!/bin/bash
set -e

echo "🔑 Google Cloud 인증 파일 다운로드 중..."

# S3에서 다운로드
aws s3 cp s3://team2-backend-wav2vec-pkl/spageti-stt-de1456d6a2c0.json /app/google-creds.json --region ap-northeast-2

# 파일 확인
if [ -f /app/google-creds.json ]; then
    echo "✅ 인증 파일 다운로드 완료"
    chmod 600 /app/google-creds.json
else
    echo "❌ 인증 파일 다운로드 실패"
    exit 1
fi

# ChromaDB 디렉토리 생성
mkdir -p /app/chroma_db

echo "🚀 FastAPI 서버 시작..."

# Uvicorn 실행
exec uvicorn main:app --host 0.0.0.0 --port 8081 --workers 2