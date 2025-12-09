# app/database/crud/presentation.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict
from ..models.presentation import (Presentation, PrVoiceFile, PrResult, PrFeedback)


# 발표 CRUD
class PresentationCRUD:

    # 발표 생성
    @staticmethod
    async def create_presentation(db: AsyncSession, user_id: int, title: str, description: Optional[str] = None, target_duration: Optional[int] = None) -> Presentation:
        presentation = Presentation(user_id=user_id, title=title, description=description, target_duration=target_duration)

        db.add(presentation)
        await db.commit()
        await db.refresh(presentation)

        return presentation

    # 발표 음성 파일 저장
    @staticmethod
    async def create_voice_file(db: AsyncSession, pr_id: int, file_path: str, original_filename: str, file_size: int) -> PrVoiceFile:
        voice_file = PrVoiceFile(pr_id=pr_id, file_path=file_path, original_filename=original_filename, file_size=file_size)

        db.add(voice_file)
        await db.commit()
        await db.refresh(voice_file)

        return voice_file

    # 분석 결과 저장
    @staticmethod
    async def create_result(db: AsyncSession, pr_id: int, v_f_id: int, analysis_data: Dict) -> PrResult:
        result = PrResult(
            pr_id=pr_id,
            v_f_id=v_f_id,
            duration=analysis_data['duration'],
            duration_min=analysis_data['duration_min'],
            total_speech_time=analysis_data['total_speech_time'],
            silence_duration=analysis_data['silence_duration'],
            silence_ratio=analysis_data['silence_ratio'],
            avg_volume_db=analysis_data['avg_volume_db'],
            max_volume_db=analysis_data['max_volume_db'],
            avg_pitch=analysis_data['avg_pitch'],
            pitch_std=analysis_data['pitch_std'],
            pitch_range=analysis_data['pitch_range'],
            speech_rate_total=analysis_data.get('speech_rate_total'),
            speech_rate_actual=analysis_data.get('speech_rate_actual'),
            num_segments=analysis_data['num_segments'],
            avg_segment_length=analysis_data['avg_segment_length'],
            energy_std=analysis_data['energy_std'],
            avg_zcr=analysis_data['avg_zcr'],
            spectral_centroid=analysis_data['spectral_centroid'],
            anxiety_ratio=analysis_data['emotion_scores'].get('Anxious'),
            embarrassment_ratio=analysis_data['emotion_scores'].get('Embarrassed')
        )

        db.add(result)
        await db.commit()
        await db.refresh(result)

        return result

    # AI가 해준 피드백 저장
    @staticmethod
    async def create_feedback(db: AsyncSession, pr_id: int, result_id: int, scores: Dict, brief_feedback: str, detailed_feedback: Dict) -> PrFeedback:
        feedback = PrFeedback(
            pr_id=pr_id,
            result_id=result_id,
            volume_score=scores['volume_score'],
            pitch_score=scores['pitch_score'],
            speed_score=scores['speed_score'],
            silence_score=scores['silence_score'],
            clarity_score=scores['clarity_score'],
            overall_score=scores['overall_score'],
            brief_feedback=brief_feedback,
            detailed_summary=detailed_feedback.get('summary'),
            detailed_strengths=detailed_feedback.get('strengths'),
            detailed_improvements=detailed_feedback.get('improvements'),
            detailed_advice=detailed_feedback.get('detailed_advice')
        )

        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        return feedback

    # 발표 데이터와 관련된 모든 데이터를 함께 조회
    @staticmethod
    async def get_presentation_with_details(db: AsyncSession, pr_id: int) -> Optional[Presentation]:
        result = await db.execute(
            select(Presentation) # 발표 테이블 선택
            .options( # 관련 데이터를 함께 조회
                selectinload(Presentation.voice_files), # 발표 음성 파일
                selectinload(Presentation.results), # 분석 결과 수치들
                selectinload(Presentation.feedbacks) # 피드백 내용
            )
            .filter(Presentation.pr_id == pr_id) # 입력 받은 발표_id
        )

        return result.scalar_one_or_none() # 조회된 결과들을 반환