from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import voice_analysis
from contextlib import asynccontextmanager


# 앱 시작 시 모델 로드
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI 서버 시작")
    try:
        from app.service.voice_analyzer import get_analyzer
        analyzer = get_analyzer()
        print("음성 분석 모델 로드 완료")
    except Exception as e:
        print(f"⚠모델 로드 실패: {e}")
    print("=" * 60)

    yield
    print("FastAPI 서버 종료")

app = FastAPI(title="Team Project API", description="음성 분석 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(voice_analysis.router)

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


@app.get("/health")
async def health():
    return {"status": "ok"}