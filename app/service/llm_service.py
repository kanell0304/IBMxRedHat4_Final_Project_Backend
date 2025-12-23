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
                # 먼저 dict로 파싱
                import json
                data = json.loads(content)

                # grade 필드 추가
                if "non_standard" in data and "score" in data["non_standard"]:
                    data["non_standard"]["grade"] = score_to_grade(data["non_standard"]["score"])

                if "filler_words" in data and "score" in data["filler_words"]:
                    data["filler_words"]["grade"] = score_to_grade(data["filler_words"]["score"])

                if "discourse_clarity" in data and "score" in data["discourse_clarity"]:
                    data["discourse_clarity"]["grade"] = score_to_grade(data["discourse_clarity"]["score"])

                if "content_overall" in data and "score" in data["content_overall"]:
                    data["content_overall"]["grade"] = score_to_grade(data["content_overall"]["score"])

                if "content_per_question" in data:
                    for per_q in data["content_per_question"]:
                        if "score" in per_q:
                            per_q["grade"] = score_to_grade(per_q["score"])

                # 이제 Pydantic 모델로 검증
                report = I_Report.model_validate(data)
                return report

            except ValidationError as e:
                raise ValueError(f"I_Report 검증 실패 : {e}")
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON 파싱 실패 : {e}")
        