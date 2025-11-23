from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database.base import Base

class IQuestion(Base):
    __tablename__="i_questions"
    
    i_question_id:Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    interview_id:Mapped[int]=mapped_column(Integer, ForeignKey("interviews.interview_id", ondelete="CASCADE"), nullable=False)
    common_question:Mapped[str]=mapped_column(String(500), nullable=False) # ?
    job_question_id:Mapped[int]=mapped_column(Integer, ForeignKey("job_questions.job_question_id"), nullable=False)
    job_question_text:Mapped[str]=mapped_column(Text, ForeignKey("job_quetions.job_question_text"), nullable=False)
    
    
    interviews:Mapped["IInterview"]=relationship(back_populates="i_questions")
    i_answers:Mapped[Optional["IAnswer"]]=relationship(back_populates="i_question", cascade="all, delete-orphan", uselist=False)
    i_question_results:Mapped[Optional["IQuestionResult"]]=relationship(back_populates="i_question", cascade="all, delete-orphan", uselist=False)