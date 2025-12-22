from openai import AsyncOpenAI
from typing import Dict, Optional, Any, List
from pydantic import ValidationError
from app.core.settings import settings
from app.prompts.interview_prompts import build_prompt, SYSTEM_MESSAGE
from app.database.schemas.interview import I_Report
from app.service.grade_utils import score_to_grade



class OpenAIService:

    def __init__(self)->None:
        self.client=AsyncOpenAI(api_key=settings.openai_api_key)
        self.model=settings.openai_model

    async def generate_report(
            self, 
            transcript:str, 
            bert_analysis:Dict,
            stt_metrics:Optional[Dict[str, Any]]=None,
            qa_list:Optional[List[Dict[str, Any]]]=None,
            )->I_Report:

            prompt=build_prompt(
                 transcript=transcript,
                 bert_analysis=bert_analysis,
                 stt_metrics=stt_metrics,
                 qa_list=qa_list
            )
            response=await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role":"system", "content":SYSTEM_MESSAGE},
                    {"role":"user", "content":prompt}
                ],
                temperature=0.3,
                response_format={"type":"json_object"}
            )

            content=response.choices[0].message.content
        
            try:
                report=I_Report.model_validate_json(content)

                report.non_standard.grade=score_to_grade(report.non_standard.score)
                report.filler_words.grade=score_to_grade(report.filler_words.score)
                report.discourse_clarity.grade=score_to_grade(report.discourse_clarity.score)

                report.content_overall.grade=score_to_grade(report.content_overall.score)

                for per_q in report.content_per_question:
                     per_q.grade=score_to_grade(per_q.score)

                return report
                
            except ValidationError as e:
                raise ValueError(f"I_Report 검증 실패 : {e}")
        