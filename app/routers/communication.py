from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.crud import communication as crud
from app.database.schemas.communication import CommunicationResponse, VoiceFileResponse, STTResultResponse, AnalysisResultResponse 
from app.service.audio_service import AudioService
from app.service.stt_service import STTService
from app.service.c_analysis_service import get_c_analysis_service
from app.core.settings import settings

router = APIRouter(prefix="/communication", tags=["Communication"])

audio_service = AudioService()
stt_service = STTService(project_id=settings.google_cloud_project_id)


@router.post("/upload", response_model=CommunicationResponse)
async def upload_wav(
    user_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    communication = await crud.create_communication(db, user_id)
    
    audio_data = await file.read()
    original_format = file.filename.split('.')[-1]
    
    wav_data, duration = audio_service.convert_to_wav(audio_data, original_format)
    
    await crud.create_voice_file(
        db=db,
        c_id=communication.c_id,
        filename=file.filename,
        original_format=original_format,
        data=wav_data,
        duration=duration
    )
    
    return communication


@router.post("/{c_id}/stt", response_model=STTResultResponse)
async def process_stt(
    c_id: int,
    db: AsyncSession = Depends(get_db)
):
    communication = await crud.get_communication_by_id(db, c_id)
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")

    voice_file = await crud.get_voice_file_by_c_id(db, c_id)
    if not voice_file:
        raise HTTPException(status_code=404, detail="Voice file not found")

    wav_data, _ = audio_service.convert_to_wav(voice_file.data, voice_file.original_format)

    chirp_result = await stt_service.transcribe_chirp(wav_data)

    stt = await crud.create_stt_result(
        db=db,
        c_id=c_id,
        c_vf_id=voice_file.c_vf_id,
        json_data=chirp_result
    )

    return stt


@router.post("/{c_id}/analyze", response_model=AnalysisResultResponse)
async def analyze_communication(
    c_id: int, target_speaker: str = "1", db: AsyncSession = Depends(get_db)
):

    # 1. Communication 존재 확인
    communication = await crud.get_communication_by_id(db, c_id)
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")

    # 2. STT 결과 조회
    stt_result = await crud.get_stt_result_by_c_id(db, c_id)
    if not stt_result:
        raise HTTPException(status_code=404, detail="STT result not found")

    # 3. 분석 서비스 호출
    analysis_service = get_c_analysis_service()

    try:
        analysis_result = await analysis_service.analyze_communication(
            stt_data=stt_result.json_data, target_speaker=target_speaker
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 중 오류 발생: {str(e)}")

    sentences = analysis_result["sentences"]
    bert_result = analysis_result["bert_result"]
    llm_result = analysis_result["llm_result"]

    # 4. 문장 리스트 저장 (c_script_sentences)
    await crud.create_script_sentences(
        db=db, c_id=c_id, c_sr_id=stt_result.c_sr_id, sentences=sentences
    )

    # 5. BERT 결과 저장 (c_bert_results)
    curse_count = bert_result.get("curse", 0)
    filler_count = bert_result.get("filler", 0)
    standard_score = (
        bert_result.get("slang", 0)
        + bert_result.get("biased", 0)
        + bert_result.get("curse", 0)
    ) / 3.0

    bert_db_result = await crud.create_bert_result(
        db=db,
        c_id=c_id,
        c_sr_id=stt_result.c_sr_id,
        target_speaker=target_speaker,
        curse_count=curse_count,
        filler_count=filler_count,
        standard_score=standard_score,
        analyzed_segments=bert_result,
    )

    # 6. 최종 결과 저장 (c_results)
    # JSON 데이터 준비 (detected_examples가 비어있으면 null)
    def prepare_json(metric_data):
        if not metric_data or not isinstance(metric_data, dict):
            return None
        detected = metric_data.get("detected_examples", [])
        if not detected:
            return None
        return {
            "detected_examples": detected,
            "reason": metric_data.get("reason", ""),
            "improvement": metric_data.get("improvement", ""),
            "revised_examples": metric_data.get("revised_examples", []),
        }

    final_result = await crud.create_result(
        db=db,
        c_id=c_id,
        c_br_id=bert_db_result.c_br_id,
        speed=llm_result.get("speed", {}).get("score", 0.0),
        speech_rate=llm_result.get("speech_rate", {}).get("score", 0.0),
        silence=llm_result.get("silence", {}).get("score", 0.0),
        clarity=llm_result.get("clarity", {}).get("score", 0.0),
        meaning_clarity=llm_result.get("meaning_clarity", {}).get("score", 0.0),
        cut=llm_result.get("cut", {}).get("score", 0),
        speed_json=prepare_json(llm_result.get("speed")),
        speech_rate_json=prepare_json(llm_result.get("speech_rate")),
        silence_json=prepare_json(llm_result.get("silence")),
        clarity_json=prepare_json(llm_result.get("clarity")),
        meaning_clarity_json=prepare_json(llm_result.get("meaning_clarity")),
        cut_json=prepare_json(llm_result.get("cut")),
        summary=llm_result.get("summary", ""),
        advice=llm_result.get("advice", ""),
    )

    return final_result


@router.get("/health")
async def stt_health_check():
    """STT 서비스 상태 확인"""
    try:
        project_id = settings.google_cloud_project_id
        return {
            "status": "ok",
            "service": "Google Speech-to-Text",
            "project_id": project_id,
            "model": "chirp_3",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}