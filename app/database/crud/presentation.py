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
        # emotion_scores 안전하게 가져오기
        emotion_scores = analysis_data.get('emotion_scores', {})
        anxiety_ratio = None
        embarrassment_ratio = None
        
        if emotion_scores:
            # 딕셔너리에서 값 추출
            anxiety_val = emotion_scores.get('Anxious')
            embarrassment_val = emotion_scores.get('Embarrassed')
            
            # float로 변환 (리스트나 다른 타입일 경우 대비)
            if anxiety_val is not None:
                anxiety_ratio = float(anxiety_val) if not isinstance(anxiety_val, (list, tuple)) else float(anxiety_val[0]) if anxiety_val else None
            if embarrassment_val is not None:
                embarrassment_ratio = float(embarrassment_val) if not isinstance(embarrassment_val, (list, tuple)) else float(embarrassment_val[0]) if embarrassment_val else None
        
        result = PrResult(
            pr_id=pr_id,
            v_f_id=v_f_id,
            duration=float(analysis_data['duration']),
            duration_min=float(analysis_data['duration_min']),
            total_speech_time=float(analysis_data['total_speech_time']),
            silence_duration=float(analysis_data['silence_duration']),
            silence_ratio=float(analysis_data['silence_ratio']),
            avg_volume_db=float(analysis_data['avg_volume_db']),
            max_volume_db=float(analysis_data['max_volume_db']),
            avg_pitch=float(analysis_data['avg_pitch']),
            pitch_std=float(analysis_data['pitch_std']),
            pitch_range=float(analysis_data['pitch_range']),
            speech_rate_total=float(analysis_data['speech_rate_total']) if analysis_data.get('speech_rate_total') is not None else None,
            speech_rate_actual=float(analysis_data['speech_rate_actual']) if analysis_data.get('speech_rate_actual') is not None else None,
            num_segments=int(analysis_data['num_segments']),
            avg_segment_length=float(analysis_data['avg_segment_length']),
            energy_std=float(analysis_data['energy_std']),
            avg_zcr=float(analysis_data['avg_zcr']),
            spectral_centroid=float(analysis_data['spectral_centroid']),
            anxiety_ratio=anxiety_ratio,
            embarrassment_ratio=embarrassment_ratio
        )

        db.add(result)
        await db.commit()
        await db.refresh(result)

        return result

    # AI가 해준 피드백 저장
    @staticmethod
    async def create_feedback(db: AsyncSession, pr_id: int, result_id: int, scores: Dict, brief_feedback: str, detailed_feedback: Dict) -> PrFeedback:
        # 각 필드를 안전하게 추출 (리스트나 튜플이 아닌 문자열로 변환)
        def safe_str(value):
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return ', '.join(str(v) for v in value)
            return str(value)
        
        feedback = PrFeedback(
            pr_id=pr_id,
            result_id=result_id,
            volume_score=int(scores.get('volume_score', 0)),
            pitch_score=int(scores.get('pitch_score', 0)),
            speed_score=int(scores.get('speed_score', 0)),
            silence_score=int(scores.get('silence_score', 0)),
            clarity_score=int(scores.get('clarity_score', 0)),
            overall_score=int(scores.get('overall_score', 0)),
            brief_feedback=brief_feedback,
            detailed_summary=safe_str(detailed_feedback.get('summary')),
            detailed_strengths=safe_str(detailed_feedback.get('strengths')),
            detailed_improvements=safe_str(detailed_feedback.get('improvements')),
            detailed_advice=safe_str(detailed_feedback.get('detailed_advice'))
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