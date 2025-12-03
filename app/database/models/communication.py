from sqlalchemy import Integer, String, Float, DateTime, Text, ForeignKey, Enum, JSON, LargeBinary, Index, UniqueConstraint, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base
import enum
from typing import Optional
from datetime import datetime


class CommunicationStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class Communication(Base):
    __tablename__ = "communication"
    c_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    status: Mapped[CommunicationStatus] = mapped_column(Enum(CommunicationStatus), nullable=False, default=CommunicationStatus.IN_PROGRESS)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="communications")
    voice_files: Mapped[list["CVoiceFile"]] = relationship("CVoiceFile", back_populates="communication", cascade="all, delete-orphan")
    stt_results: Mapped[list["CSTTResult"]] = relationship("CSTTResult", back_populates="communication", cascade="all, delete-orphan")
    script_sentences: Mapped[list["CScriptSentence"]] = relationship("CScriptSentence", back_populates="communication", cascade="all, delete-orphan")
    bert_result: Mapped[Optional["CBERTResult"]] = relationship("CBERTResult", back_populates="communication", uselist=False, cascade="all, delete-orphan")
    result: Mapped[Optional["CResult"]] = relationship("CResult", back_populates="communication", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_id', 'user_id'),  # 특정 사용자의 모든 대화 조회 시 사용
        Index('idx_created_at', 'created_at'),  # 대화목록 최신순 정렬 시 사용
    )

class CVoiceFile(Base):
    __tablename__ = "c_voice_files"
    c_vf_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    c_id: Mapped[int] = mapped_column(Integer, ForeignKey('communication.c_id', ondelete='CASCADE'), nullable=False, index=True)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_format: Mapped[str] = mapped_column(String(10), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary(length=4294967295), nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    
    communication: Mapped["Communication"] = relationship("Communication", back_populates="voice_files")
    stt_results: Mapped[list["CSTTResult"]] = relationship("CSTTResult", back_populates="voice_file", cascade="all, delete-orphan")
    
    __table_args__ = (Index('idx_c_id', 'c_id'),) # 특정 대화의 음성파일 조회 시 사용


class CSTTResult(Base):
    __tablename__ = "c_stt_results"
    c_sr_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    c_id: Mapped[int] = mapped_column(Integer, ForeignKey('communication.c_id', ondelete='CASCADE'), nullable=False, index=True)
    c_vf_id: Mapped[int] = mapped_column(Integer, ForeignKey('c_voice_files.c_vf_id', ondelete='CASCADE'), nullable=False, index=True)

    json_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    communication: Mapped["Communication"] = relationship("Communication", back_populates="stt_results")
    voice_file: Mapped["CVoiceFile"] = relationship("CVoiceFile", back_populates="stt_results")
    script_sentences: Mapped[list["CScriptSentence"]] = relationship("CScriptSentence", back_populates="stt_result", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('c_id', name='uq_c_id'),
                      # 한 c_id당 STT 결과 1개만 허용
                      Index('idx_c_id', 'c_id'), # 특정 대화의 STT 결과 조회 시 사용
                      Index('idx_c_vf_id', 'c_vf_id'),) # 특정 음성파일의 STT 결과 조회 시 사용


class CScriptSentence(Base):
    __tablename__ = "c_script_sentences"
    c_ss_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    c_id: Mapped[int] = mapped_column(Integer, ForeignKey('communication.c_id', ondelete='CASCADE'), nullable=False)
    c_sr_id: Mapped[int] = mapped_column(Integer, ForeignKey('c_stt_results.c_sr_id', ondelete='CASCADE'), nullable=False)

    sentence_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 스크립트 내 순서 (0부터)
    speaker_label: Mapped[str] = mapped_column(String(20), nullable=False)  # "0", "1", "2" ...
    text: Mapped[str] = mapped_column(Text, nullable=False)  
    start_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) 
    end_time: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    communication: Mapped["Communication"] = relationship("Communication", back_populates="script_sentences")
    stt_result: Mapped["CSTTResult"] = relationship("CSTTResult", back_populates="script_sentences")

    __table_args__ = (
        Index('idx_c_id', 'c_id'),
        Index('idx_sentence_index', 'c_id', 'sentence_index'),  # 정렬 조회용
        UniqueConstraint('c_id', 'sentence_index', name='uq_c_id_sentence_index')
    )


class CBERTResult(Base):
    __tablename__ = "c_bert_results"
    c_br_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    c_id: Mapped[int] = mapped_column(Integer, ForeignKey('communication.c_id', ondelete='CASCADE'), nullable=False, unique=True)
    c_sr_id: Mapped[int] = mapped_column(Integer, ForeignKey('c_stt_results.c_sr_id', ondelete='CASCADE'), nullable=False)

    target_speaker: Mapped[str] = mapped_column(String(20), nullable=False, default="1")
    curse_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    filler_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    standard_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    analyzed_segments: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    
    communication: Mapped["Communication"] = relationship("Communication", back_populates="bert_result")
    result: Mapped[Optional["CResult"]] = relationship("CResult", back_populates="bert_result", uselist=False, cascade="all, delete-orphan")


class CResult(Base):
    __tablename__ = "c_results"
    c_result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    c_id: Mapped[int] = mapped_column(Integer, ForeignKey('communication.c_id', ondelete='CASCADE'), nullable=False, unique=True)
    c_br_id: Mapped[int] = mapped_column(Integer, ForeignKey('c_bert_results.c_br_id', ondelete='CASCADE'), nullable=False, unique=True)

    # 점수들
    speed: Mapped[float] = mapped_column(Float, nullable=False)
    speech_rate: Mapped[float] = mapped_column(Float, nullable=False)
    silence: Mapped[float] = mapped_column(Float, nullable=False)
    clarity: Mapped[float] = mapped_column(Float, nullable=False)
    meaning_clarity: Mapped[float] = mapped_column(Float, nullable=False)
    cut: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # detected_examples, reason, improvement, revised_examples 저장하는 JSON 컬럼 
    # 내용 없으면 null로 저장
    speed_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    speech_rate_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    silence_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    clarity_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    meaning_clarity_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    cut_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 전체 요약 및 조언
    summary: Mapped[str] = mapped_column(Text, nullable=False, default='')
    advice: Mapped[str] = mapped_column(Text, nullable=False, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    communication: Mapped["Communication"] = relationship("Communication", back_populates="result")
    bert_result: Mapped["CBERTResult"] = relationship("CBERTResult", back_populates="result")