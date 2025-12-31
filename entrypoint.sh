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

echo "📦 HuggingFace 모델 캐시 복원 중..."
mkdir -p /root/.cache/huggingface/hub

# S3에서 캐시 다운로드 (있으면)
if aws s3 cp s3://team2-backend-wav2vec-pkl/cache/huggingface-cache.tar.gz /tmp/ --region ap-northeast-2 2>/dev/null; then
    echo "✅ 캐시 다운로드 완료, 압축 해제 중..."
    tar -xzf /tmp/huggingface-cache.tar.gz -C /root/.cache/huggingface/hub/
    rm /tmp/huggingface-cache.tar.gz
    echo "✅ 모델 캐시 복원 완료 (시작 시간 단축!)"
else
    echo "⚠️  캐시 없음 - 첫 시작 시 모델 다운로드됨 (2-3분 소요)"
fi

# ChromaDB 디렉토리 생성
mkdir -p /app/chroma_db

echo "🗄️  데이터베이스 마이그레이션 실행 중..."
alembic upgrade head || {
    echo "⚠️  Alembic 마이그레이션 실패 - Python으로 직접 실행 시도..."
    python3 << 'PYEOF'
from sqlalchemy import create_engine, text
import os

try:
    url = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    engine = create_engine(url)
    
    with engine.connect() as conn:
        # alembic_version 설정
        conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version VALUES ('7c9a4e8f4dcb')"))
        
        # 컴럼 추가 (이미 있으면 무시)
        for col in ['curse', 'filler', 'biased', 'slang']:
            try:
                conn.execute(text(f"ALTER TABLE c_results ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"))
                print(f"✅ {col} 컴럼 추가")
            except Exception as e:
                if "Duplicate column" in str(e):
                    print(f"ℹ️  {col} 컴럼 이미 존재")
        
        conn.commit()
        print("✅ 데이터베이스 스키마 업데이트 완료")
except Exception as e:
    print(f"❌ 데이터베이스 업데이트 실패: {e}")
PYEOF
}

echo "🚀 FastAPI 서버 시작..."

# Uvicorn 실행
exec uvicorn main:app --host 0.0.0.0 --port 8081 --workers 2