from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict
from ..database.crud.presentation import PresentationCRUD
from .voice_analyzer import get_analyzer
from .presentation_scorer import PresentationScorer
from .presentation_feedback_service import PresentationFeedbackService


class PresentationAnalysisService:

    def __init__(self):
        self.analyzer = get_analyzer() # 분석 값 불러오기
        self.scorer = PresentationScorer() # 점수화 값 불러오기
        self.feedback_service = PresentationFeedbackService() # 피드백 불러오기

    # 음성을 분석 -> 점수화 -> 피드백 생성 -> DB에 모두 저장
    async def analyze_and_save(self, db: AsyncSession, pr_id: int, v_f_id: int, audio_path: str, estimated_syllables: int = None) -> Dict:
        # 음성 분석
        analysis_result = self.analyzer.analyze(audio_path=audio_path, estimated_syllables=estimated_syllables)

        if "error" in analysis_result:
            raise ValueError(f"Analysis failed: {analysis_result['error']}")

        # 분석 결과 저장
        pr_result = await PresentationCRUD.create_result(db=db, pr_id=pr_id, v_f_id=v_f_id, analysis_data=analysis_result)

        # 점수 계산
        scores = self.scorer.calculate_scores(analysis_result)

        # AI가 준 피드백 생성
        brief_feedback = await self.feedback_service.generate_brief_feedback(result=analysis_result, scores=scores)

        detailed_feedback = await self.feedback_service.generate_detailed_feedback(result=analysis_result, scores=scores)

        # 피드백 저장
        pr_feedback = await PresentationCRUD.create_feedback(db=db, pr_id=pr_id, result_id=pr_result.result_id, scores=scores, brief_feedback=brief_feedback, detailed_feedback=detailed_feedback)

        # frontend 응답 데이터 구성
        return {
            "success": True, # 성공 여부
            "data": {
                "result_id": pr_result.result_id,
                "feedback_id": pr_feedback.feedback_id,
                "brief_feedback": brief_feedback, # 간단한 피드백
                "detailed_feedback": { # 자세한 피드백 데이터 모음
                    "summary": detailed_feedback.get('summary'), # 발표 요약 및 전반적 평가 (전체적으로 어땠는지)
                    "strengths": detailed_feedback.get('strengths'), # 잘한 점
                    "improvements": detailed_feedback.get('improvements'), # 개선할 점
                    "advice": detailed_feedback.get('detailed_advice') # 상세 조언
                },
                "scores": scores,  # 다각형 다이어그램용
                "raw_metrics": {  # 프론트엔드에서 필요시 표시
                    "duration_min": analysis_result['duration_min'], # 발표 시간(분) ex) 1.4 -> 1.4 x 60(초) -> 84초 -> 1분 24초
                    "avg_volume_db": analysis_result['avg_volume_db'], # 평균 음량(db)
                    "avg_pitch": analysis_result['avg_pitch'], # 평균 음높이(Hz)
                    "silence_ratio": analysis_result['silence_ratio'], # 침묵 비율
                    "speech_rate": analysis_result.get('speech_rate_actual'), # 발화 속도(음절/초)
                    "emotion": analysis_result.get('emotion'), # 감정
                    "emotion_confidence": analysis_result.get('emotion_confidence') # 감정 신뢰도(%) - 67.89 = 67.89%
                }
            }
        }


_service = None


def get_presentation_analysis_service():
    global _service
    if _service is None:
        _service = PresentationAnalysisService()
    return _service