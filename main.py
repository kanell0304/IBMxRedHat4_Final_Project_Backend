from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import voice_analysis
from app.routers import bert
from contextlib import asynccontextmanager


# 앱 시작 시 모델 로드
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("서버 시작")
    try:
        from app.service.voice_analyzer import get_analyzer
        analyzer = get_analyzer()
        print("음성 분석 모델 로드")
    except Exception as e:
        print(f"모델 로드 실패: {e}")
    yield
    print("서버 종료")

app = FastAPI(title="Team Project API", description="음성 분석 API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

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

# 서버 구동 상태 확인
@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(bert.router)