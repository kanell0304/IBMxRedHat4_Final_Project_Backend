from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.database.models.interview import InterviewType


# 문제 표현과 수정 표현을 한 쌍으로 묶음
class RevisedExample(BaseModel):
    original:str
    revised:str

# 개별 지표 분석
class IndexAnalysis(BaseModel):
    score:int=Field(..., ge=0, le=100, description="0~100점 척도")
    detected_examples:List[str]=Field(default_factory=list)
    reason:str
    improvement:str
    revised_examples:List[RevisedExample]=Field(default_factory=list) # 문제 문장과 개선 문장을 매핑하여 리스트화

# 최종 리포트
class I_Report(BaseModel):
    non_standard:IndexAnalysis
    filler_words:IndexAnalysis
    discourse_clarity:IndexAnalysis
    overall_comment:str=Field(..., description="전반적인 총평")

class AnalyzeReq(BaseModel):
    transcript:str=Field(..., description="STT 변환 면접 답변 텍스트")


# process
class ProcessAnswerResponse(BaseModel):
    transcript: str
    sentences: List[Dict[str, Any]]
    label_counts: Dict[str, int]


class AnswerUploadResponse(BaseModel):
    answer_id: int
    audio_format: str
    size: int


class I_StartReq(BaseModel):
    user_id: int
    question_type: str = Field(..., description="common | job | mixed | (공통질문만/직무관련/섞어서)")
    job_group: Optional[str] = Field(default=None, description="프론트 선택값 매핑용(필수 아님)")
    job_role: Optional[str] = Field(default=None, description="직무 관련/섞어서 선택 시 필수")
    difficulty: Optional[str] = Field(default=None, description="easy | mid | hard (선택)")
    total_questions: int = Field(default=5, gt=0, description="랜덤으로 선택할 질문 수")


class I_StartQ(BaseModel):
    q_id: int
    q_order: int
    question_text: str
    class Config:
        from_attributes = True


class I_StartRes(BaseModel):
    i_id: int
    questions: List[I_StartQ]


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


# 답변 응답
class Answer(BaseModel):
    i_answer_id: int
    i_id: int
    q_id: Optional[int] = None
    q_order: Optional[int] = None
    duration_sec: Optional[int] = None
    transcript: Optional[str] = None
    labels_json: Optional[Dict[str, Any]] = None
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
    i_answer_id: Optional[int] = None
    q_id: Optional[int] = None
    overall: Optional[str] = None
    class Config:
        from_attributes = True
