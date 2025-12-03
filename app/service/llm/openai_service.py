import json
from openai import AsyncOpenAI
from typing import Dict
from app.core.settings import settings
from app.prompts.interview_prompts import build_prompt, SYSTEM_MESSAGE
from app.service.llm.base import BaseLLMService


class OpenAIService(BaseLLMService):

    def __init__(self):
        self.client=AsyncOpenAI(api_key=settings.openai_api_key)
        self.model=settings.openai_model


    async def generate_report(self, transcript:str, bert_analysis:Dict):
        try:
            prompt=build_prompt(transcript, bert_analysis)

            response=await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role":"system", "content":SYSTEM_MESSAGE},
                    {"role":"user", "content":prompt}
                ],
                temperature=0.3,
                response_format={"type":"json_object"}
            )

            result=json.loads(response.choices[0].message.content)
            return result
        
        except json.JSONDecodeError as e:
            raise ValueError(f"OpenAI 응답 JSON 파싱 실패 : {e}")
        