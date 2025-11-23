from sqlalchemy import String, Integer, func, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import List
from app.database.base import Base

class Interview(Base):
    __tablename__="interviews"
    
    interview_id:Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:Mapped[int]=mapped_column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    job_category_id:Mapped[int]=mapped_column(Integer, ForeignKey("job_categories.job_category_id"), nullable=False)
    total_duration:Mapped[int]=mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, server_default=func.now(), nullable=False)
    status: Mapped[str]=mapped_column(String(50)) # ?
    
  
    i_questions:Mapped[List["IQuestion"]]=relationship(back_populates="interview", cascade="all, delete-orphan")
    i_final_results:Mapped["IFinalResult"]=relationship(back_populates="interview", cascade="all, delete-orphan", uselist=False)