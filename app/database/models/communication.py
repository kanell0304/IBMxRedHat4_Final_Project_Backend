from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import relationship


class Communication(Base):
    __tablename__ = "communication"
    c_id = Column(Integer, primary_key=True, autoincrement=True)
    c_title = Column(String(200), nullable=False)
    c_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(30), nullable=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    m_category_id = Column(Integer, ForeignKey("main_category.m_category_id"), nullable=False)
    results = relationship("CommunicationResult", cascade="all, delete-orphan")


class CommunicationResult(Base):
    __tablename__ = "c_result"
    c_result_id = Column(Integer, primary_key=True, autoincrement=True)
    c_id = Column(Integer, ForeignKey("communication.c_id"), nullable=False)
    create_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sentence_speed = Column(Integer, nullable=True)
    silence = Column(Integer, nullable=True)
    filler = Column(Integer, nullable=True)
    curse = Column(Integer, nullable=True)
    clearly_meaning = Column(Integer, nullable=True)
    clarity = Column(Integer, nullable=True)
    cut = Column(Integer, nullable=True)
    feedback_body = Column(Text, nullable=True)
