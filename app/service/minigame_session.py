from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid


class GameMode:
    TARGET_COUNT = "target_count"
    TIME_LIMIT = "time_limit"


class GameSession(BaseModel):
    session_id: str
    difficulty: str
    mode: str
    target_count: Optional[int] = None
    time_limit: Optional[int] = None
    used_sentence_ids: List[int] = []
    scores: List[float] = []
    current_sentence_id: Optional[int] = None
    started_at: datetime


class MiniGameSessionManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}

    def create_session(self, difficulty: str,  mode: str, target_count: Optional[int] = None, time_limit: Optional[int] = None) -> GameSession:
        session_id = str(uuid.uuid4())

        session = GameSession(
            session_id=session_id,
            difficulty=difficulty,
            mode=mode,
            target_count=target_count,
            time_limit=time_limit,
            started_at=datetime.utcnow()
        )

        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[GameSession]:
        return self.sessions.get(session_id)

    def add_used_sentence(self, session_id: str, sentence_id: int):
        session = self.sessions.get(session_id)
        if session and sentence_id not in session.used_sentence_ids:
            session.used_sentence_ids.append(sentence_id)

    def set_current_sentence(self, session_id: str, sentence_id: int):
        session = self.sessions.get(session_id)
        if session:
            session.current_sentence_id = sentence_id

    def add_score(self, session_id: str, score: float):
        session = self.sessions.get(session_id)
        if session:
            session.scores.append(score)

    def get_average_score(self, session_id: str) -> float:
        session = self.sessions.get(session_id)
        if session and session.scores:
            return round(sum(session.scores) / len(session.scores), 2)
        return 0.0

    def is_game_finished(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return True

        if session.mode == GameMode.TARGET_COUNT:
            return len(session.scores) >= session.target_count

        return False

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]


session_manager = MiniGameSessionManager()