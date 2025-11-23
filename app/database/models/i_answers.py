from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class IAnswer(Base):
    __tablename__ = "i_answers"
    
    i_answer_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    i_question_id: Mapped[int] = mapped_column(Integer, ForeignKey("i_questions.i_question_id", ondelete="CASCADE"), nullable=False, unique=True)
    audio_path: Mapped[str] = mapped_column(String(500), nullable=False)
    

    i_question: Mapped["IQuestion"] = relationship(back_populates="i_answer")