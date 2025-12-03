from typing import Dict
from app.service.i_inference_service import get_inference_service
from app.service.llm.openai_service import OpenAIService
from app.service.llm.watsonx_service import WatsonxService
from app.database.schemas.interview import InterviewReport
from app.core.settings import settings


class AnalysisService:

    def __init__(self):
        self.bert_service=get_inference_service() # infernece_service 가져옴
        self.llm_service=self.get_llm_service() # LLM_PROVIDER 보고 서비스 결정


    def get_llm_service(self):
        if settings.llm_provider=="openai":
            return OpenAIService()
        elif settings.llm_provider=="watsonx":
            return WatsonxService()
        else:
            raise ValueError(f"지원하지 않는 LLM_PROVIDER : {settings.llm_provider}")
        
    async def analyze_interview(self, transcript:str):

        # BERT 멀티 라벨 분류
        bert_result=self.bert_service.predict_labels(transcript)

        # LLM report 생성
        report_dict=await self.llm_service.generate_report(
            transcript=transcript,
            bert_analysis=bert_result
        )

        # pydantic 검증
        report=InterviewReport(**report_dict)
        return report


# 싱글턴 인스턴스
analysis_service=None

def get_analysis_service():
    global analysis_service
    if analysis_service is None:
        analysis_service=AnalysisService()
    return analysis_service