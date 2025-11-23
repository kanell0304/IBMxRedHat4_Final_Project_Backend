from sqlalchemy import Integer, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.database.base import Base


class IFinalResult(Base):
    __tablename__="i_final_results"
    
    i_final_result_id:Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:Mapped[int]=mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    interview_id:Mapped[int]=mapped_column(Integer, ForeignKey("interviews.interview_id", ondelete="CASCADE"), nullable=False, unique=True)
 

    avg_formal:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_sentence_speed:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_clarity:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_sentiment:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_score:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    

    overall_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overall_advice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


    # 전체 종합 결과니까 사용자의 강점과 약점도 같이 제시해주면 더 풍부해질 것 같아서 
    # strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # weaknesses: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    

    interview: Mapped["Interview"] = relationship(back_populates="i_final_result")