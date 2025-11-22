from sqlalchemy.dialects.mysql import LONGBLOB

from ..base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from sqlalchemy import String, func, DateTime, Integer, ForeignKey, Column
from typing import Optional, List

# 사용자 테이블
class VoiceFile(Base):
    __tablename__="voice_files"

    vf_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vf_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    data = Column(LONGBLOB, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)


    user: Mapped["User"] = relationship("User", back_populates="voice_files")