from pydantic import BaseModel, Field
from typing import List, Dict, Any


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
class InterviewReport(BaseModel):
    non_standard:IndexAnalysis
    filler_words:IndexAnalysis
    discourse_clarity:IndexAnalysis
    overall_comment:str=Field(..., description="전반적인 총평")

class AnalyzeRequest(BaseModel):
    transcript:str=Field(..., description="STT 변환 면접 답변 텍스트")


# process
class ProcessAnswerResponse(BaseModel):
    transcript: str
    labels: Dict[str, Any]


class AnswerUploadResponse(BaseModel):
    answer_id: int
    audio_path: str
