from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..database.models.minigame import MiniGameSentence
from ..service.minigame_session import session_manager, GameMode
from ..service.scoring_service import ScoringService
from ..service.audio_service import AudioService
from ..service.stt_service import STTService
from ..core.settings import settings
from typing import Optional
import random

router = APIRouter(prefix="/api/minigame", tags=["minigame"])

audio_service = AudioService()
stt_service = STTService(project_id=settings.google_cloud_project_id)
scoring_service = ScoringService()


def flatten_transcript(stt_json: dict) -> str:
    parts = []
    for res in stt_json.get("results", []):
        for alt in res.get("alternatives", []):
            if alt.get("transcript"):
                parts.append(alt["transcript"])
    return " ".join(parts).strip()


@router.post("/start")
async def start_game(difficulty: str = Form(...), mode: str = Form(...), target_count: Optional[int] = Form(None), time_limit: Optional[int] = Form(None),):
    if difficulty not in ["easy", "medium", "hard"]:
        raise HTTPException(status_code=400, detail="Invalid difficulty")

    if mode == GameMode.TARGET_COUNT and not target_count:
        raise HTTPException(status_code=400, detail="target_count is required")

    if mode == GameMode.TIME_LIMIT and not time_limit:
        raise HTTPException(status_code=400, detail="time_limit is required")

    session = session_manager.create_session(
        difficulty=difficulty,
        mode=mode,
        target_count=target_count,
        time_limit=time_limit
    )

    return {
        "session_id": session.session_id,
        "difficulty": session.difficulty,
        "mode": session.mode,
        "target_count": session.target_count,
        "time_limit": session.time_limit
    }


@router.get("/sentence/{session_id}")
async def get_next_sentence(session_id: str, db: Session = Depends(get_db)):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query = db.query(MiniGameSentence).filter(
        MiniGameSentence.difficulty == session.difficulty,
        ~MiniGameSentence.id.in_(session.used_sentence_ids)
    )

    remaining_count = query.count()
    if remaining_count == 0:
        raise HTTPException(status_code=404, detail="No more sentences available")

    random_offset = random.randint(0, remaining_count - 1)
    sentence = query.offset(random_offset).first()

    session_manager.set_current_sentence(session_id, sentence.id)
    session_manager.add_used_sentence(session_id, sentence.id)

    return {
        "sentence_id": sentence.id,
        "sentence": sentence.sentence,
        "difficulty": sentence.difficulty,
        "category": sentence.category
    }


async def process_audio_background(session_id: str, audio_bytes: bytes, file_format: str, sentence_text: str):
    try:
        wav_data, _ = audio_service.convert_to_wav(audio_bytes, file_format)

        stt_json = await stt_service.transcribe_chirp(wav_data)
        recognized_text = flatten_transcript(stt_json)

        score = scoring_service.calculate_accuracy(sentence_text, recognized_text)

        session_manager.add_score(session_id, score)

        print(f"Session {session_id}: Original='{sentence_text}', Recognized='{recognized_text}', Score={score}")

    except Exception as e:
        print(f"Background processing error: {str(e)}")
        session_manager.add_score(session_id, 0.0)


@router.post("/evaluate")
async def evaluate_audio(background_tasks: BackgroundTasks, session_id: str = Form(...), audio_file: UploadFile = File(...), db: Session = Depends(get_db)):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.current_sentence_id:
        raise HTTPException(status_code=400, detail="No current sentence")

    sentence = db.query(MiniGameSentence).filter(MiniGameSentence.id == session.current_sentence_id).first()

    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")

    audio_bytes = await audio_file.read()
    file_format = audio_file.filename.split(".")[-1] if audio_file.filename else "webm"

    background_tasks.add_task(
        process_audio_background,
        session_id,
        audio_bytes,
        file_format,
        sentence.sentence
    )

    return {
        "status": "processing",
        "message": "음성 분석 중입니다"
    }


@router.get("/status/{session_id}")
async def get_game_status(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session.session_id,
        "mode": session.mode,
        "difficulty": session.difficulty,
        "completed_count": len(session.scores),
        "target_count": session.target_count,
        "scores": session.scores,
        "is_finished": session_manager.is_game_finished(session_id)
    }


@router.post("/finish/{session_id}")
async def finish_game(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    average_score = session_manager.get_average_score(session_id)

    result = {
        "session_id": session.session_id,
        "difficulty": session.difficulty,
        "mode": session.mode,
        "completed_count": len(session.scores),
        "scores": session.scores,
        "average_score": average_score,
        "total_attempts": len(session.used_sentence_ids)
    }

    session_manager.delete_session(session_id)

    return result


@router.get("/sentences")
async def get_sentences(difficulty: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(MiniGameSentence)

    if difficulty:
        query = query.filter(MiniGameSentence.difficulty == difficulty)

    sentences = query.all()
    return {"sentences": sentences, "count": len(sentences)}