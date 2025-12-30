from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import voice_analysis, user, interview, jobs, image, presentation, communication, community, minigame
from contextlib import asynccontextmanager
from app.database.database import create_tables
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n서버 시작")

    try:
        create_tables()
    except Exception as e:
        print(f"테이블 생성 실패: {e}")

    try:
        import os
        if os.getenv("APP_ENV", "").lower() in {"local", "dev"} and os.getenv("AUTO_SEED", "false").lower() in {"1","true","yes","y"}:
            from app.seeds.seed_runner import run_seed_if_needed
            from app.database.database import get_db_session

            db = next(get_db_session())
            try:
                run_seed_if_needed(db)
                print("로컬 DB 시드 완료")
            finally:
                db.close()
    except Exception as e:
        print(f"로컬 DB 시드 실패: {e}")

    # 미니게임 기본 데이터 초기화 추가
    try:
        from app.utils.init_minigame_data import init_default_sentences
        from app.database.database import get_db_session

        db = next(get_db_session())
        try:
            init_default_sentences(db)
            print("미니게임 기본 문제 초기화 완료")
        finally:
            db.close()
    except Exception as e:
        print(f"미니게임 데이터 초기화 실패: {e}")

    # 1. 모델 파일 확인 (로컬 우선, 없으면 S3)
    try:
        from app.core.model_loader import ensure_models_ready
        models_ready = ensure_models_ready()

        if not models_ready:
            print("일부 모델 파일이 없습니다. 일부 기능이 제한될 수 있습니다.")
    except Exception as e:
        print(f"모델 파일 확인 실패: {e}")

    # 2. 음성 분석기 로드
    try:
        from app.service.voice_analyzer import get_analyzer
        analyzer = get_analyzer()
        print("음성 분석 모델 로드 완료")
    except Exception as e:
        print(f"모델 로드 실패: {e}")

    print("")
    yield
    print("\n서버 종료")


app = FastAPI(title="Team Project API", description="음성 분석 API", version="1.0.0", lifespan=lifespan)

# CORS 설정: 환경 변수에서 허용할 도메인 목록 가져오기
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://api.st-each.com"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(communication.router)
app.include_router(community.router)
app.include_router(image.router)
app.include_router(interview.router)
app.include_router(jobs.router)
app.include_router(presentation.router)
app.include_router(user.router)
app.include_router(voice_analysis.router)
app.include_router(minigame.router)


@app.get("/")
async def root():
    return {
        "message": "Team Project API",
        "version": "1.0.0",
        "endpoints": {
            "voice_analysis": "/voice/analyze",
            "minigame": "/api/minigame",  # 추가
            "health_check": "/voice/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok"}