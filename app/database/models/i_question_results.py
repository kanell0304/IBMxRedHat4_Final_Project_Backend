from sqlalchemy import Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database.base import Base


class IQuestionResult(Base):
    __tablename__="i_question_results"
    
    i_question_result_id:Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    i_question_id:Mapped[int]=mapped_column(Integer, ForeignKey("i_questions.i_question_id", ondelete="CASCADE"), nullable=False, unique=True)
    

    formal:Mapped[Optional[float]]=mapped_column(Float, nullable=True)
    sentence_speed:Mapped[Optional[float]]=mapped_column(Float, nullable=True)
    clarity:Mapped[Optional[float]]=mapped_column(Float, nullable=True)
    sentiment:Mapped[Optional[float]]=mapped_column(Float, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    advice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    
    i_question: Mapped["IQuestion"] = relationship(back_populates="i_question_result")