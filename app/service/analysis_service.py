from app.service.i_bert_service import get_inference_service
from app.service.llm.openai_service import OpenAIService
from app.database.schemas.interview import InterviewReport

class AnalysisService:

    def __init__(self):
        self.bert_service=get_inference_service()
        self.llm_service=OpenAIService

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