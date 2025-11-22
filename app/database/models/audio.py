from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.database.database import Base
from datetime import datetime


class VoiceFile(Base):
    __tablename__ = "voice_file"
    v_f_id = Column(Integer, primary_key=True, autoincrement=True)
    v_f_name = Column(String(255), nullable=False)
    create_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    data = Column(Text, nullable=True)
    pr_id = Column(Integer, ForeignKey("presentation.pr_id"), nullable=True)
