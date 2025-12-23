from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from ..models.communication import (
    Communication,
    CVoiceFile,
    CSTTResult,
    CScriptSentence,
    CBERTResult,
    CResult,
)
from typing import Optional, List

# 대화분석 CRUD

async def create_communication(db: AsyncSession, user_id: int) -> Communication:
    communication = Communication(user_id=user_id)
    db.add(communication)
    await db.commit()
    await db.refresh(communication)
    return communication


async def get_communication_by_id(db: AsyncSession, c_id: int) -> Optional[Communication]:
    result = await db.execute(
        select(Communication).where(Communication.c_id == c_id)
    )
    return result.scalar_one_or_none()


async def get_communication_with_details(db: AsyncSession, c_id: int) -> Optional[Communication]:
    result = await db.execute(
        select(Communication)
        .where(Communication.c_id == c_id)
        .options(
            selectinload(Communication.voice_files),
            selectinload(Communication.stt_results),
            selectinload(Communication.script_sentences),
            selectinload(Communication.bert_result),
            selectinload(Communication.result)
        )
    )
    return result.scalar_one_or_none()


async def get_communications_by_user_id(db: AsyncSession, user_id: int) -> List[Communication]:
    result = await db.execute(
        select(Communication)
        .where(Communication.user_id == user_id)
        .order_by(Communication.created_at.desc())
    )
    return list(result.scalars().all())


async def get_all_communications(db: AsyncSession) -> List[Communication]:
    result = await db.execute(
        select(Communication).order_by(Communication.created_at.desc())
    )
    return list(result.scalars().all())


async def create_voice_file(db: AsyncSession, c_id: int, filename: str, original_format: str, data: bytes, duration: Optional[float]) -> CVoiceFile:
    voice_file = CVoiceFile(
        c_id=c_id,
        filename=filename,
        original_format=original_format,
        data=data,
        duration=duration
    )
    db.add(voice_file)
    await db.commit()
    await db.refresh(voice_file)
    return voice_file


async def create_stt_result(db: AsyncSession, c_id: int, c_vf_id: int, json_data: dict) -> CSTTResult:
    stt_result = CSTTResult(
        c_id=c_id,
        c_vf_id=c_vf_id,
        json_data=json_data
    )
    db.add(stt_result)
    await db.commit()
    await db.refresh(stt_result)
    return stt_result


async def get_voice_file_by_c_id(db: AsyncSession, c_id: int) -> Optional[CVoiceFile]:
    result = await db.execute(
        select(CVoiceFile).where(CVoiceFile.c_id == c_id)
    )
    return result.scalar_one_or_none()

# c_id로 STT 결과 조회
async def get_stt_result_by_c_id(db: AsyncSession, c_id: int) -> Optional[CSTTResult]:
    result = await db.execute(select(CSTTResult).where(CSTTResult.c_id == c_id))
    return result.scalar_one_or_none()


async def create_script_sentences(
    db: AsyncSession, c_id: int, c_sr_id: int, sentences: List[dict]
) -> List[CScriptSentence]:
    sentence_objects = []
    for sent in sentences:
        sentence_obj = CScriptSentence(
            c_id=c_id,
            c_sr_id=c_sr_id,
            sentence_index=sent["sentence_index"],
            speaker_label=sent["speaker_label"],
            text=sent["text"],
            start_time=sent.get("start_time"),
            end_time=sent.get("end_time"),
            feedback=sent.get("feedback"),
        )
        sentence_objects.append(sentence_obj)
        db.add(sentence_obj)

    await db.commit()
    for obj in sentence_objects:
        await db.refresh(obj)

    return sentence_objects


# c_id로 스크립트 문장들 조회 (sentence_index 순서대로 정렬)
async def get_script_sentences_by_c_id(
    db: AsyncSession, c_id: int
) -> List[CScriptSentence]:
    result = await db.execute(
        select(CScriptSentence)
        .where(CScriptSentence.c_id == c_id)
        .order_by(CScriptSentence.sentence_index)
    )
    return list(result.scalars().all())


async def create_bert_result(
    db: AsyncSession,
    c_id: int,
    c_sr_id: int,
    target_speaker: str,
    curse: int,
    filler: int,
    biased: int,
    slang: int,
    analyzed_segments: dict,
) -> CBERTResult:

    bert_result = CBERTResult(
        c_id=c_id,
        c_sr_id=c_sr_id,
        target_speaker=target_speaker,
        curse=curse,
        filler=filler,
        biased=biased,
        slang=slang,
        analyzed_segments=analyzed_segments,
    )
    db.add(bert_result)
    await db.commit()
    await db.refresh(bert_result)
    return bert_result


async def create_result(
    db: AsyncSession,
    c_id: int,
    c_br_id: int,
    speaking_speed: float,
    silence: float,
    clarity: float,
    meaning_clarity: float,
    cut: int,
    speaking_speed_json: Optional[dict],
    silence_json: Optional[dict],
    clarity_json: Optional[dict],
    meaning_clarity_json: Optional[dict],
    cut_json: Optional[dict],
    summary: str,
    advice: str,
) -> CResult:

    result = CResult(
        c_id=c_id,
        c_br_id=c_br_id,
        speaking_speed=speaking_speed,
        silence=silence,
        clarity=clarity,
        meaning_clarity=meaning_clarity,
        cut=cut,
        speaking_speed_json=speaking_speed_json,
        silence_json=silence_json,
        clarity_json=clarity_json,
        meaning_clarity_json=meaning_clarity_json,
        cut_json=cut_json,
        summary=summary,
        advice=advice,
    )
    db.add(result)
    await db.commit()
    await db.refresh(result)
    return result


async def delete_analysis_results_by_c_id(db: AsyncSession, c_id: int):
    await db.execute(delete(CResult).where(CResult.c_id == c_id))
    await db.execute(delete(CBERTResult).where(CBERTResult.c_id == c_id))
    await db.execute(delete(CScriptSentence).where(CScriptSentence.c_id == c_id))
    await db.commit()


async def delete_communication_by_c_id(db: AsyncSession, c_id: int):
    await db.execute(delete(CResult).where(CResult.c_id == c_id))
    await db.execute(delete(CBERTResult).where(CBERTResult.c_id == c_id))
    await db.execute(delete(CScriptSentence).where(CScriptSentence.c_id == c_id))
    await db.execute(delete(CSTTResult).where(CSTTResult.c_id == c_id))
    await db.execute(delete(CVoiceFile).where(CVoiceFile.c_id == c_id))
    await db.execute(delete(Communication).where(Communication.c_id == c_id))
    await db.commit()