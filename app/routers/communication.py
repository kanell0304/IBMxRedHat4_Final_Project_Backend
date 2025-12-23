from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.crud import communication as crud
from app.database.schemas.communication import CommunicationResponse, VoiceFileResponse, STTResultResponse, AnalysisResultResponse, CommunicationDetailResponse
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
    
    try:
        wav_data, duration = audio_service.convert_to_wav(audio_data, original_format)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=f"오디오 변환 실패: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오디오 처리 중 오류: {str(e)}")
    
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

    # 기존 STT 결과가 있다면 삭제 (재시도 지원)
    # create_stt_result 내부에서 commit을 수행하므로, 여기서 미리 삭제하고 commit해야 UniqueConstraint 에러 방지
    try:
        existing_stt = await crud.get_stt_result_by_c_id(db, c_id)
        if existing_stt:
            print(f"Deleting existing STT result for c_id={c_id}")
            await db.delete(existing_stt)
            await db.commit()
    except Exception as e:
        print(f"Error deleting existing STT result: {e}")
        await db.rollback()

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

    # 3. 재실행 대비 기존 분석 결과 삭제
    await crud.delete_analysis_results_by_c_id(db, c_id)

    # 4. 분석 서비스 호출
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

    # 5. sentence_feedbacks 매핑 (문장별 피드백 추가)
    sentence_feedbacks_map = {}
    if "sentence_feedbacks" in llm_result:
        for item in llm_result["sentence_feedbacks"]:
            sentence_idx = item["sentence_index"]
            feedbacks = item.get("feedbacks", [])
            sentence_feedbacks_map[sentence_idx] = feedbacks

    # 각 문장에 feedback 추가
    for sentence in sentences:
        idx = sentence["sentence_index"]
        if idx in sentence_feedbacks_map:
            sentence["feedback"] = sentence_feedbacks_map[idx]
        else:
            sentence["feedback"] = None

    # 6. 문장 리스트 저장 (c_script_sentences)
    await crud.create_script_sentences(
        db=db, c_id=c_id, c_sr_id=stt_result.c_sr_id, sentences=sentences
    )

    # 6. BERT 결과 저장 (c_bert_results)
    # 6. BERT 결과 저장 (c_bert_results)
    curse = bert_result.get("curse", 0)
    filler = bert_result.get("filler", 0)
    biased = bert_result.get("biased", 0)
    slang = bert_result.get("slang", 0)
    
    # standard_score 제거됨 (모델 변경 대응)

    bert_db_result = await crud.create_bert_result(
        db=db,
        c_id=c_id,
        c_sr_id=stt_result.c_sr_id,
        target_speaker=target_speaker,
        curse=curse,
        filler=filler,
        biased=biased,
        slang=slang,
        analyzed_segments=bert_result,
    )

    # 7. 최종 결과 저장 (c_results)
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
        }

    final_result = await crud.create_result(
        db=db,
        c_id=c_id,
        c_br_id=bert_db_result.c_br_id,
        speaking_speed=llm_result.get("speaking_speed", {}).get("score", 0.0),
        silence=llm_result.get("silence", {}).get("score", 0.0),
        clarity=llm_result.get("clarity", {}).get("score", 0.0),
        meaning_clarity=llm_result.get("meaning_clarity", {}).get("score", 0.0),
        cut=llm_result.get("cut", {}).get("score", 0),
        speaking_speed_json=prepare_json(llm_result.get("speaking_speed")),
        silence_json=prepare_json(llm_result.get("silence")),
        clarity_json=prepare_json(llm_result.get("clarity")),
        meaning_clarity_json=prepare_json(llm_result.get("meaning_clarity")),
        cut_json=prepare_json(llm_result.get("cut")),
        summary=llm_result.get("summary", ""),
        advice=llm_result.get("advice", ""),
    )

    return final_result


@router.get("/{c_id}", response_model=CommunicationDetailResponse)
async def get_communication_detail(c_id: int, db: AsyncSession = Depends(get_db)):
    communication = await crud.get_communication_with_details(db, c_id)
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")

    # Pydantic 모델로 변환하여 데이터 가공
    response = CommunicationDetailResponse.model_validate(communication)

    # detected_examples의 sentence_index를 실제 문장으로 변환
    if response.result and communication.script_sentences:
        # sentence_index -> text 매핑 생성
        sentence_map = {s.sentence_index: s.text for s in communication.script_sentences}

        # 각 JSON 필드의 detected_examples 변환
        json_fields = ['speaking_speed_json', 'silence_json',
                       'clarity_json', 'meaning_clarity_json', 'cut_json']

        for field_name in json_fields:
            json_data = getattr(response.result, field_name, None)
            if json_data and isinstance(json_data, dict):
                detected = json_data.get('detected_examples', [])
                if detected:
                    # sentence_index를 문장 텍스트로 변환 (리스트 컴프리헨션)
                    json_data['detected_examples'] = [
                        sentence_map.get(idx, f"문장 {idx}") for idx in detected
                    ]

    # [수정] standard_score 계산 및 slang 통합 (DB 컬럼 삭제 대응)
    if response.bert_result:
        b = response.bert_result

        # 1. 점수 계산 (4개 지표 모두 포함)
        # 각 지표는 카운트 값이므로, 총합을 구한 후 최대값으로 나눠서 0~1 범위로 정규화
        total_issues = b.slang + b.biased + b.curse + b.filler
        max_possible = 4  # 각 지표가 1번씩만 발생한다고 가정한 최대값

        # 문제가 적을수록 높은 점수 (10점 만점)
        if total_issues == 0:
            b.standard_score = 10.0
        else:
            # 문제 개수에 따라 감점 (1개당 -2.5점)
            b.standard_score = max(0.0, 10.0 - (total_issues * 2.5))

        # 2. [Fix] 프론트엔드 '욕설' 그래프에 '비속어(slang)'도 포함
        # 피드백에서 slang을 curse로 통합했으므로, 표시되는 카운트도 합산
        b.curse = b.curse + b.slang

    return response


@router.get("/users/{user_id}/communications", response_model=list[CommunicationResponse])
async def list_user_communications(user_id: int, db: AsyncSession = Depends(get_db)):
    communications = await crud.get_communications_by_user_id(db, user_id)
    return communications


@router.get("", response_model=list[CommunicationResponse])
async def list_all_communications(db: AsyncSession = Depends(get_db)):
    communications = await crud.get_all_communications(db)
    return communications


@router.delete("/{c_id}")
async def delete_communication(c_id: int, db: AsyncSession = Depends(get_db)):
    communication = await crud.get_communication_by_id(db, c_id)
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")

    await crud.delete_communication_by_c_id(db, c_id)
    return {"message": "Communication deleted successfully"}


@router.get("/{c_id}/audio")
async def get_audio_file(c_id: int, db: AsyncSession = Depends(get_db)):
    voice_file = await crud.get_voice_file_by_c_id(db, c_id)
    if not voice_file:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # WAV 파일로 반환
    return Response(
        content=voice_file.data,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f"inline; filename={voice_file.filename}",
            "Accept-Ranges": "bytes"
        }
    )


@router.get("/health")
async def stt_health_check():
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