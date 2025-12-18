from sqlalchemy import Column, Integer, String, Enum
from ..database import Base
import enum


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class MiniGameSentence(Base):
    __tablename__ = "minigame_sentences"

    id = Column(Integer, primary_key=True, index=True)
    sentence = Column(String(500), nullable=False, unique=True)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.EASY)
    category = Column(String(50), nullable=True)
    length = Column(Integer, nullable=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.sentence:
            self.length = len(self.sentence.replace(" ", ""))