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
    grade:str=Field(..., description="S/A/B/C/D 등급")
    detected_examples:List[str]=Field(default_factory=list, description="이 지표와 관련된 문제가 드러난 실제 문장 예시")
    reason:str=Field(..., description="왜 이런 평가가 나왔는지에 대한 설명")
    improvement:str=Field(..., description="어떻게 개선하면 좋을지에 대한 가이드")
    revised_examples:List[RevisedExample]=Field(default_factory=list, description="문제 문장과 개선 문장을 매핑하여 리스트화")

# 내용 전체 평가 + 질문별 평가
class ContentOverall(BaseModel):
    score:int=Field(..., ge=0, le=100, description="전체 답변의 내용 적절성 점수")
    grade:str=Field(..., description="S/A/B/C/D 등급")
    strengths:List[str]=Field(default_factory=list, description="내용적으로 잘한 점")
    weaknesses:List[str]=Field(default_factory=list, description="내용적으로 부족한 점")
    summary:str=Field(..., description="내용 측면에서의 한 문단 요약")

class PerQuestionContent(BaseModel):
    q_index:int=Field(..., description="질문 번호")
    q_text:str=Field(..., description="질문 텍스트")
    user_answer:str=Field(default="", description="사용자 답변 원문")
    score:int=Field(..., ge=0, le=100, description="해당 질문에 대한 답변 내용 적절성 점수")
    grade:str=Field(..., description="S/A/B/C/D 등급")
    comment:str=Field(..., description="이 답변이 왜 적절/부적절했는지 내용 중심 코멘트")
    suggestion:str=Field(..., description="어떻게 말하면 더 좋았을지에 대한 구체적 제안")
    question_intent:str=Field(default="", description="질문 의도 요약")
    is_appropriate:bool=Field(default=True, description="답변이 질문 의도에 맞는지 여부")
    evidence_sentences:List[str]=Field(default_factory=list, description="근거가 되는 문장들")


# 최종 리포트
class I_Report(BaseModel):
    non_standard:IndexAnalysis=Field(..., description="비표준어/속어 사용 분석")
    filler_words:IndexAnalysis=Field(..., description="군말/망설임 분석")
    discourse_clarity:IndexAnalysis=Field(..., description="담화/문장 구조의 명료성")
    content_overall:ContentOverall=Field(..., description="전체 답변의 내용 적절성 평가")
    content_per_question:List[PerQuestionContent]=Field(default_factory=list, description="각 질문별 내용 적절성 평가")
    overall_comment:str=Field(..., description="전반적인 총평")

class I_Report_En(BaseModel):
    score:int=Field(..., ge=0, le=100, description="종합 점수(0~100)")
    grade:str=Field(..., description="S/A/B/C/D 등급")
    comments:List[str]=Field(..., description="평가 코멘트 리스트")
    improvements:List[str]=Field(..., description="개선사항 리스트")
    stt_metrics:Dict[str, Any]=Field(..., description="STT metrics")

    
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
    answer_id: int
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
    language: str = Field(default="ko")


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
    language: str = "ko"
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
    report: I_Report | PerQuestionContent | Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

    @field_validator('report', mode='before')
    @classmethod
    def parse_report(cls, v):
        if not isinstance(v, dict):
            return v

        # report 구조로 타입 판단
        if 'q_index' in v and 'q_text' in v:
            try:
                return PerQuestionContent(**v)
            except Exception:
                pass

        if 'non_standard' in v or 'filler_words' in v:
            try:
                return I_Report(**v)
            except Exception:
                pass

        # 파싱 실패 시 dict 그대로 반환
        return v
    

# 인터뷰 직후 결과
class QuestionDetailEvaluation(BaseModel):
    q_index:int
    q_text:str
    user_answer:str=Field(..., description="사용자가 말한 답변 원문")
    question_intent:str=Field(..., description="질문 의도 요약")
    is_appropriate:bool=Field(..., description="답변이 질문 의도에 맞는지 여부")
    feedback:str=Field(..., description="개선 가이드")
    evidence_sentences:List[str]=Field(default_factory=list, description="근거가 되는 문장")


class SimilarAnswerHint(BaseModel):
    message:str=Field(..., description="유사 답변 힌트 메시지")
    answer_id:int=Field(..., description="유사한 과거 answer_id")
    similarity:float=Field(..., description="유사도 점수")


class ImmediateResultResponse(BaseModel):
    i_id:int
    overall_report:I_Report | I_Report_En=Field(..., description="인터뷰 총평")
    question_details:List[QuestionDetailEvaluation]=Field(..., description="질문별 세부 평가")
    similar_hint:Optional[SimilarAnswerHint]=Field(None, description="유사 답변 힌트 (3회 이상일 때만 해당)")


# 히스토리 : 말버릇/약점 분석
class EvidenceSentence(BaseModel):
    text:str=Field(..., description="실제 사용자가 말한 문장")
    answer_id:int=Field(..., description="해당 answer_id")
    session_id:int=Field(..., description="interview session_id")


class SimilarAnswerLink(BaseModel):
    answer_id:int=Field(..., description="유사한 answer_id")
    text_preview:str=Field(..., description="답변 미리보기")
    similarity:float=Field(..., description="유사도")


class WeaknessDetail(BaseModel):
    label_name:str=Field(..., description="약점 라벨")
    label_display_name:str=Field(..., description="약점 라벨 ver.ko")
    avg_score:float=Field(..., description="평균 점수")
    occurrence_count:int=Field(..., description="발생 횟수")
    evidence_sentences:List[EvidenceSentence]=Field(..., description="증거 문장 2~3개")
    similar_answers:List[SimilarAnswerLink]=Field(..., description="유사 답변 링크")
    improvement_guide:str=Field(..., description="개선 가이드")


class WeaknessCardResponse(BaseModel):
    total_interviews:int=Field(..., description="총 인터뷰 수")
    has_enough_data:bool=Field(..., description="3회 이상 데이터가 있는지")
    top_weaknesses:List[WeaknessDetail]=Field(..., description="약점 TOP 3")
    summary:str=Field(..., description="전체 약점 요약")


# 히스토리 : 지표 변화
class MetricChange(BaseModel):
    metric_name:str=Field(..., description="지표 이름")
    previous_avg:float=Field(..., description="이전 3회 평균값")
    recent_avg:float=Field(..., description="최근 3회 평균값")
    change_percent:float=Field(..., description="변화율")
    direction:str=Field(..., description="up / down / stable")
    is_positive:bool=Field(..., description="긍정적 변화인지 여부")


class MetricChangeCardResponse(BaseModel):
    total_interviews:int=Field(..., description="총 한국어 인터뷰 수")
    has_enough_data:bool=Field(..., description="6회 이상 데이터가 있는지 여부")
    significant_changes:List[MetricChange]=Field(..., description="변화가 큰 지표들")
    summary:str=Field(..., description="전체 변화 요약 문장")

