from typing import Dict
from .llm_service import OpenAIService
from ..prompts.presentation_prompts import build_brief_prompt, build_detailed_prompt


# 발표 음성 결과를 openai api에 프롬프트를 통해 전달 후 간단한 피드백, 자세한 피드백 받기
class PresentationFeedbackService:

    def __init__(self):
        self.openai_service = OpenAIService()

    # 간단한 피드백 생성 (2-3문장)
    async def generate_brief_feedback(self, result: Dict, scores: Dict) -> str:
        prompt = build_brief_prompt(result, scores)

        try:
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
        
        except Exception as e:
            print(f"OpenAI API 오류 (간단한 피드백): {str(e)}")
            # 오류 발생 시 기본 피드백 반환
            return f"분석이 완료되었습니다. 종합 점수: {scores.get('overall_score', 0)}점. 나머지 분석은 자세한 피드백을 참고해주세요."

    # 자세한 피드백 생성 (각 항목별 상세 분석)
    async def generate_detailed_feedback(self, result: Dict, scores: Dict) -> Dict[str, str]:
        prompt = build_detailed_prompt(result, scores)

        try:
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
            content = response.choices[0].message.content
            
            # JSON 파싱 시도
            try:
                feedback_dict = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"JSON 파싱 실패: {content}")
                # 기본값 반환
                feedback_dict = {
                    "summary": content[:200] if content else "분석 완료",
                    "strengths": "분석 중 오류 발생",
                    "improvements": "다시 시도해주세요",
                    "detailed_advice": ""
                }
            
            # 필수 키 확인 및 기본값 설정
            required_keys = ['summary', 'strengths', 'improvements', 'detailed_advice']
            for key in required_keys:
                if key not in feedback_dict:
                    feedback_dict[key] = ""
            
            return feedback_dict
            
        except Exception as e:
            print(f"OpenAI API 오류: {str(e)}")
            # 오류 발생 시 기본 피드백 반환
            return {
                "summary": "분석 중 오류가 발생했습니다.",
                "strengths": "다시 시도해주세요.",
                "improvements": "",
                "detailed_advice": ""
            }