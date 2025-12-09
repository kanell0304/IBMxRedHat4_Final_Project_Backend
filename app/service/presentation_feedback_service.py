from typing import Dict
from .llm.openai_service import OpenAIService
from ..prompts.presentation_prompts import build_brief_prompt, build_detailed_prompt


# 발표 음성 결과를 openai api에 프롬프트를 통해 전달 후 간단한 피드백, 자세한 피드백 받기
class PresentationFeedbackService:

    def __init__(self):
        self.openai_service = OpenAIService()

    # 간단한 피드백 생성 (2-3문장)
    async def generate_brief_feedback(self, result: Dict, scores: Dict) -> str:
        prompt = build_brief_prompt(result, scores)

        response = await self.openai_service.client.chat.completions.create(
            model=self.openai_service.model,
            messages=[
                {"role": "system", "content": "당신은 발표 코치입니다. 간결하고 핵심적인 피드백을 제공하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=200
        )

        return response.choices[0].message.content

    # 자세한 피드백 생성 (각 항목별 상세 분석)
    async def generate_detailed_feedback(self, result: Dict, scores: Dict) -> Dict[str, str]:
        prompt = build_detailed_prompt(result, scores)

        response = await self.openai_service.client.chat.completions.create(
            model=self.openai_service.model,
            messages=[
                {"role": "system", "content": "당신은 전문 발표 코치입니다. 구체적이고 실행 가능한 피드백을 제공하세요."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        import json
        feedback_dict = json.loads(response.choices[0].message.content)
        return feedback_dict