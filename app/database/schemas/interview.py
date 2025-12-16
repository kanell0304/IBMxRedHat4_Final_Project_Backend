from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from app.database.models.interview import InterviewType
from app.database.models.interview import ResultScope


# STT stats schemas
class DurationStats(BaseModel):
    total_sec:float=Field(..., description="전체 발화 시간")
    avg_sec_per_answer:float=Field(..., description="답변 1개당 평균 발화 시간")

class SpeechRateStats(BaseModel):
    avg_wpm:float=Field(..., description="평균 발화 속도(WPM)")
    min_wpm:float
    max_wpm:float
    std_wpm:float

class PauseStats(BaseModel):
    total_count:int=Field(..., description="전체 pause 횟수")
    avg_duration:float=Field(..., description="전체 pause 길이")
    avg_silence_ratio:float
    max_silence_ratio:float
    worst_silence_answer_id:Optional[int]=None

class STTQualityStats(BaseModel):
    avg_confidence: float
    min_confidence: float
    avg_low_conf_ratio: float
    max_low_conf_ratio: float
    worst_confidence_answer_id: Optional[int] = None

# 인터뷰 전체의 STT 기반 통계 요약
class InterviewSTTMetrics(BaseModel):
    i_id:int
    num_answers:int
    num_answers_with_metrics:int
    num_answers_without_metrics:int

    duration:DurationStats
    speech_rate:SpeechRateStats
    pause:PauseStats
    stt_quality:STTQualityStats


# LLM report schemas
# 문제 표현과 수정 표현을 한 쌍으로 묶음
class RevisedExample(BaseModel):
    original:str=Field(..., description="사용자가 말한 원문장")
    revised:str=Field(..., description="개선된 표현")

# 개별 지표 분석
class IndexAnalysis(BaseModel):
    score:int=Field(..., ge=0, le=100, description="0~100점 척도 점수")
    detected_examples:List[str]=Field(default_factory=list, description="이 지표와 관련된 문제가 드러난 실제 문장 예시")
    reason:str=Field(..., description="왜 이런 평가가 나왔는지에 대한 설명")
    improvement:str=Field(..., description="어떻게 개선하면 좋을지에 대한 가이드")
    revised_examples:List[RevisedExample]=Field(default_factory=list, description="문제 문장과 개선 문장을 매핑하여 리스트화")

# 내용 전체 평가 + 질문별 평가
class ContentOverall(BaseModel):
    score:int=Field(..., ge=0, le=100, description="전체 답변의 내용 적절성 점수")
    strengths:List[str]=Field(default_factory=list, description="내용적으로 잘한 점")
    weaknesses:List[str]=Field(default_factory=list, description="내용적으로 부족한 점")
    summary:str=Field(..., description="내용 측면에서의 한 문단 요약")

class PerQuestionContent(BaseModel):
    q_index:int=Field(..., description="질문 번호")
    q_text:str=Field(..., description="질문 텍스트")
    score:int=Field(..., ge=0, le=100, description="해당 질문에 대한 답변 내용 적절성 점수")
    comment:str=Field(..., description="이 답변이 왜 적절/부적절했는지 내용 중심 코멘트")
    suggestion:str=Field(..., description="어떻게 말하면 더 좋았을지에 대한 구체적 제안")


# 최종 리포트
class I_Report(BaseModel):
    non_standard:IndexAnalysis=Field(..., description="비표준어/속어 사용 분석")
    filler_words:IndexAnalysis=Field(..., description="군말/망설임 분석")
    discourse_clarity:IndexAnalysis=Field(..., description="담화/문장 구조의 명료성")
    content_overall:ContentOverall=Field(..., description="전체 답변의 내용 적절성 평가")
    content_per_question:List[PerQuestionContent]=Field(default_factory=list, description="각 질문별 내용 적절성 평가")
    overall_comment:str=Field(..., description="전반적인 총평")

    
class AnalyzeReq(BaseModel):
    i_id:int=Field(..., description="인터뷰 고유 ID")
    interview_type:InterviewType=Field(..., description="인터뷰타입")
    transcript:str=Field(..., description="STT 변환 면접 답변 텍스트")
    bert_analysis:Dict[str, Any]=Field(default_factory=dict, description="BERT 멀티라벨 분석 결과`")
    stt_stats:InterviewSTTMetrics=Field(..., description="STT 기반 인터뷰 전체 발화 통계")
    created_at:datetime=Field(..., description="인터뷰 생성 시각")


# process
class ProcessAnswerResponse(BaseModel):
    transcript: str
    sentences: List[Dict[str, Any]]
    label_counts: Dict[str, int]


class AnswerUploadResponse(BaseModel):
    answer_id: int
    audio_format: str
    size: int
    transcript: Optional[str] = None
    duration_sec: Optional[int] = None
    stt_metrics: Optional[Dict[str, Any]] = None

class AnswerUploadProcessResponse(BaseModel):
    answer_id: int
    audio_format: str
    size: int
    transcript: Optional[str] = None
    duration_sec: Optional[int] = None
    stt_metrics: Optional[Dict[str, Any]] = None
    bert_analysis: Optional[Dict[str, Any]] = None
    sentences: Optional[List[Dict[str, Any]]] = None
    label_counts: Optional[Dict[str, int]] = None

# 인터뷰 시작/질문 관련
class I_StartReq(BaseModel):
    user_id: int
    question_type: str = Field(..., description="common | job | mixed | (공통질문만/직무관련/섞어서)")
    job_group: Optional[str] = Field(default=None, description="프론트 선택값 매핑용(필수 아님)")
    job_role: Optional[str] = Field(default=None, description="직무 관련/섞어서 선택 시 필수")
    difficulty: Optional[str] = Field(default=None, description="easy | mid | hard (선택)")
    total_questions: int = Field(default=5, gt=0, description="랜덤으로 선택할 질문 수")
    language: str = Field(default="ko", description="질문 언어 코드 (예: ko, en)")


class I_StartQ(BaseModel):
    q_id: int
    q_order: int
    question_text: str
    class Config:
        from_attributes = True


class I_StartRes(BaseModel):
    i_id: int
    questions: List[I_StartQ]
    language: str = "ko"


# 인터뷰 기본/상세/답변 스키마
# 인터뷰 생성
class I_Create(BaseModel):
    user_id: int
    interview_type: InterviewType
    category_id: Optional[int] = None
    total_questions: int = Field(default=5, gt=0)


# 인터뷰 목록
class I_Basic(BaseModel):
    i_id: int
    user_id: int
    interview_type: InterviewType
    category_id: Optional[int] = None
    status: Optional[int] = None
    total_questions: int
    current_question: int
    created_at: datetime
    class Config:
        from_attributes = True


# 답변 생성
class AnswerCreate(BaseModel):
    q_id: Optional[int] = None
    q_order: Optional[int] = None
    duration_sec: Optional[int] = Field(default=None, ge=0)
    transcript: Optional[str] = None
    labels_json: Optional[Dict[str, Any]] = None
    stt_metrics_json: Optional[Dict[str, Any]] = None


# 답변 응답
class Answer(BaseModel):
    i_answer_id: int
    i_id: int
    q_id: int
    q_order: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# 상세 인터뷰
class I_Detail(I_Basic):
    answers: List[Answer] = Field(default_factory=list)

# 결과
class I_Result(BaseModel):
    i_result_id: int
    i_id: int
    scope: ResultScope
    report: I_Report
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

    # DB dict를 I_Report 자동 변환
    @field_validator('report', mode='before')
    @classmethod
    def parse_report(cls, v):
        if isinstance(v, dict):
            return I_Report(**v)
        return v