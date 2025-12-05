from sqlalchemy import DateTime, ForeignKey, String, Integer, Float, Text, func
from app.database.database import Base
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List


# 발표 테이블
class Presentation(Base):
    __tablename__ = "presentations"
    
    pr_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False) # 어떤 이용자의 것인지
    title: Mapped[str] = mapped_column(String(200), nullable=False) # 발표 제목
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 발표에 대한 설명
    target_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 목표 발표 시간(초)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False) # 생성일
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 진행 상태 표시(미완료: 0, 완료: 1)
    m_category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('main_category.m_category_id', ondelete='SET NULL'))

    voice_files: Mapped[List["PrVoiceFile"]] = relationship("PrVoiceFile", back_populates="presentation", cascade="all, delete-orphan")
    main_category: Mapped[Optional["MainCategory"]] = relationship("MainCategory", back_populates="presentations")
    results: Mapped[List["PrResult"]] = relationship("PrResult", back_populates="presentation", cascade="all, delete-orphan")
    feedbacks: Mapped[List["PrFeedback"]] = relationship("PrFeedback", back_populates="presentation", cascade="all, delete-orphan")


# 음성 파일 테이블
class PrVoiceFile(Base):
    __tablename__ = "pr_voice_files"
    
    v_f_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pr_id: Mapped[int] = mapped_column(ForeignKey("presentations.pr_id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False) # s3 or 로컬 파일 경로
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False) # 원본 파일 이름
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 파일 크기
    # file_format: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # 파일 확장자 # 혹시 몰라서 작성만
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False) # 업로드 날짜

    presentation: Mapped["Presentation"] = relationship("Presentation", back_populates="voice_files")
    results: Mapped[List["PrResult"]] = relationship("PrResult", back_populates="voice_file", cascade="all, delete-orphan")


# 음성 분석 결과 테이블
class PrResult(Base):
    __tablename__ = "pr_results"
    
    result_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pr_id: Mapped[int] = mapped_column(ForeignKey("presentations.pr_id"), nullable=False)
    v_f_id: Mapped[int] = mapped_column(ForeignKey("pr_voice_files.v_f_id"), nullable=False)
    
    # 기본 시간 정보
    duration: Mapped[float] = mapped_column(Float, nullable=False) # 전체 오디오 길이(초)
    duration_min: Mapped[float] = mapped_column(Float, nullable=False) # 전체 오디오 길이(분)
    total_speech_time: Mapped[float] = mapped_column(Float, nullable=False) # 실제 발화 시간(초)
    silence_duration: Mapped[float] = mapped_column(Float, nullable=False) # 침묵 구간 총 시간(초)
    silence_ratio: Mapped[float] = mapped_column(Float, nullable=False) # 침묵 비율(0~1) => 0.23 => 전체의 23%
    
    # 음량 분석
    avg_volume_db: Mapped[float] = mapped_column(Float, nullable=False) # 평균 음량(dB)
    max_volume_db: Mapped[float] = mapped_column(Float, nullable=False) # 최고 음량(dB)
    
    # 음높이(피치) 분석
    avg_pitch: Mapped[float] = mapped_column(Float, nullable=False) # 평균 피치/음높이(Hz)
    pitch_std: Mapped[float] = mapped_column(Float, nullable=False) # 피치 표준편차(억양 변화)
    pitch_range: Mapped[float] = mapped_column(Float, nullable=False) # 피치 범위(최고-최저)
    
    # 발화 속도 - 아래의 두 값을 비교하여 차이가 크다면 중간에 쉬는 텀(침묵)이 많다는 것 ex) 침묵 수치가 너무 적다면 말을 너무 빠르게 쉬지않고 말하는 것
    speech_rate_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 전체 시간 기준 발화 속도 # 침묵, 휴지(휴식)시간을 포함해서 단어를 말하는 속도 ex) 300단어를 5분간 말함 => 300/5 = 60
    speech_rate_actual: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 실제 발화 시간 기준 속도 # 침묵, 휴지(휴식)시간을 제외한 단어를 말하는 속도 ex) 5분짜리 발표에서 300 단어를 3분간 말함 => 300/3 = 100

    # 세그먼트 분석
    num_segments: Mapped[int] = mapped_column(Integer, nullable=False) # 발화 세그먼트 개수
    avg_segment_length: Mapped[float] = mapped_column(Float, nullable=False) # 평균 세그먼트 길이(초)
    
    # 음성 특성 (고급 분석)
    energy_std: Mapped[float] = mapped_column(Float, nullable=False) # 에너지 표준편차(강약 조절)
    avg_zcr: Mapped[float] = mapped_column(Float, nullable=False) # 평균 영교차율(명료도)
    spectral_centroid: Mapped[float] = mapped_column(Float, nullable=False) # 스펙트럴 중심(음색)
    
    # 감정 분석 (불안/당황 비율, 합=100)
    anxiety_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 불안 비율(%) ex) 70
    embarrassment_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # 당황 비율(%) ex) 30
    
    analyzed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False) # 분석 완료 시간

    presentation: Mapped["Presentation"] = relationship("Presentation", back_populates="results")
    voice_file: Mapped["PrVoiceFile"] = relationship("PrVoiceFile", back_populates="results")
    feedbacks: Mapped[List["PrFeedback"]] = relationship("PrFeedback", back_populates="result", cascade="all, delete-orphan")


# 발표 피드백 테이블
class PrFeedback(Base):
    __tablename__ = "pr_feedbacks"
    
    feedback_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    pr_id: Mapped[int] = mapped_column(ForeignKey("presentations.pr_id"), nullable=False)
    result_id: Mapped[int] = mapped_column(ForeignKey("pr_results.result_id"), nullable=False)

    # 평가 점수 (100점 만점)
    volume_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 음량 적절성 점수
    pitch_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 억양/음높이 점수
    speed_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 발화 속도 점수
    clarity_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 명료도 점수
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 종합 점수
    
    # 감정 분석 결과
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # 주된 감정 (불안/당황 중 비율 높은 것)
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # 자신감 수준: high/medium/low (음성 특성+감정 비율로 계산)
    
    # AI 피드백 텍스트
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 발표 요약 및 전반적 평가
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 잘한 점
    improvements: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 개선할 점
    detailed_advice: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # 상세 조언
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False) # 분석 생성일

    presentation: Mapped["Presentation"] = relationship("Presentation", back_populates="feedbacks")
    result: Mapped["PrResult"] = relationship("PrResult", back_populates="feedbacks")
