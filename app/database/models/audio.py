from sqlalchemy import DateTime, ForeignKey, String, func
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional


class VoiceFile(Base):
    __tablename__ = "voice_file"
    v_f_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    v_f_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    data: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pr_id: Mapped[Optional[int]] = mapped_column(ForeignKey("presentation.pr_id"), nullable=True)
