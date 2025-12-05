from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import create_tables
from app.routers import voice_analysis, user
from contextlib import asynccontextmanager
from app.core.model_loader import ensure_models_ready
from app.service.voice_analyzer import get_analyzer

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n서버 시작")

    # 1. 모델 파일 확인 (로컬 우선, 없으면 S3)1
    try:
        models_ready = ensure_models_ready()

        if not models_ready:
            print("일부 모델 파일이 없습니다. 일부 기능이 제한될 수 있습니다.")
    except Exception as e:
        print(f"모델 파일 확인 실패: {e}")

    # 2. 음성 분석기 로드
    try:
        analyzer = get_analyzer()
        print("음성 분석 모델 로드 완료")
    except Exception as e:
        print(f"모델 로드 실패: {e}")

    # 데이터베이스 테이블 생성
    try:
        create_tables()
    except Exception as e:
        print(f"데이터베이스 테이블 생성 실패: {e}")

    print("")
    yield
    print("\n서버 종료")


app = FastAPI(title="Team Project API", description="음성 분석 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_analysis.router)
app.include_router(user.router)

@app.get("/")
async def root():
    return {
        "message": "Team Project API",
        "version": "1.0.0",
        "endpoints": {
            "voice_analysis": "/voice/analyze",
            "health_check": "/voice/health",
            "docs": "/docs"
        }
    }

# 서버 구동 상태 확인
@app.get("/health")
async def health():
    return {"status": "ok"}