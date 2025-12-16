from openai import AsyncOpenAI
from typing import Dict, Optional, Any, List
from pydantic import ValidationError
from app.core.settings import settings
from app.prompts.interview_prompts import build_prompt, SYSTEM_MESSAGE
from app.database.schemas.interview import I_Report



class OpenAIService:

    def __init__(self)->None:
        self.client=AsyncOpenAI(api_key=settings.openai_api_key)
        self.model=settings.openai_model

    async def generate_report(
            self, 
            transcript:str, 
            bert_analysis:Dict,
            stt_metrics:Optional[Dict[str, Any]]=None,
            weakness_pattern:Optional[Dict[str, Any]]=None,
            evolution_insights:Optional[Dict[str, Any]]=None,
            qa_list:Optional[List[Dict[str, Any]]]=None,
            )->I_Report:

            prompt=build_prompt(
                 transcript=transcript,
                 bert_analysis=bert_analysis,
                 stt_metrics=stt_metrics,
                 weakness_patterns=weakness_pattern,
                 evolution_insights=evolution_insights,
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
                return I_Report.model_validate_json(content)
            except ValidationError as e:
                raise ValueError(f"I_Report 검증 실패 : {e}")
        