import os
from typing import Dict, Any, List
from app.core.settings import settings
from app.database.models.interview import InterviewAnswer
from app.infra.chroma_db import collection, get_embedding

# 텍스트를 임베딩하고 ChromaDB에 저장
def save_chroma(answer_id: int, session_id: int, question_no: int, text: str, labels: Dict[str, Any]):
  embedding = get_embedding(text)  # 텍스트를 숫자로 임베딩

  # 벡터, 원문, 메타데이터를 한 묶음으로 collection에 저장
  collection.add(
    ids=[f"answer_{answer_id}"], # 고유 ID로 재검색 시 바로 특정
    documents=[text],# 검색 결과로 보여줄 실제 답변 텍스트
    metadatas=[{
      "answer_id": answer_id, # DB 답변 ID (추적용)
      "session_id": session_id, # 같은 인터뷰 세션 묶음 식별
      "question_no": question_no,
      **labels, # BERT 결과도 함께 저장해 필터/검색용으로 활용
    }],
    embeddings=[embedding], # 유사도 검색의 핵심 데이터
  )

# 이전 이름 호환
store_answer_in_chroma = save_chroma
chroma = save_chroma

# STT로 받은 값 데이터에서 transcript만 모아 한 문장으로 합침
def _extract_transcript(stt_result: Dict[str, Any]) -> str:
  transcripts: List[str] = []
  for item in stt_result.get("results", []):
    for alt in item.get("alternatives", []):
      text = alt.get("transcript")
      if text:
        transcripts.append(text.strip())
  if not transcripts:
    raise ValueError("transcript 없음")
  return " ".join(transcripts)


# 모의면접용
def _i_predict_labels(text: str) -> Dict[str, Any]:
  from app.service.i_bert_service import get_inference_service
  service = get_inference_service()
  return service.predict_labels(text)

# 모의면접용
async def i_process_answer(answer_id: int, db):
  answer: InterviewAnswer | None = await db.get(InterviewAnswer, answer_id)
  transcript = answer.transcript

  # STT
  if not transcript:
    if not answer.audio_path:
      raise ValueError("audio_path가 없어 STT를 수행할 수 없습니다.")

    with open(answer.audio_path, "rb") as f:
      audio_bytes = f.read()

    original_format = os.path.splitext(answer.audio_path)[1].lstrip(".") or "wav"

    from app.service.audio_service import AudioService
    from app.service.stt_service import STTService

    wav_data, _ = AudioService.convert_to_wav(audio_bytes, original_format)  # 포맷 통일
    stt_service = STTService(project_id=settings.google_cloud_project_id) # Google STT 클라이언트 준비
    stt_result = await stt_service.transcribe_chirp(wav_data) # STT 호출
    transcript = _extract_transcript(stt_result) # 텍스트만 추출

  # BERT 분류
  labels = _i_predict_labels(transcript)

  # mysql에 올리기
  answer.transcript = transcript
  answer.labels_json = labels
  await db.commit()
  await db.refresh(answer)

  # chromadb 저장
  save_chroma(
    answer_id=answer.i_answer_id,
    session_id=answer.i_id,
    question_no=answer.q_order or 0,
    text=transcript,
    labels=labels,
  )

  return {
    "transcript": transcript,
    "labels": labels,
  }

# 대화분석용
def _predict_comm_labels(text: str) -> Dict[str, Any]:
  from app.service.c_bert_service import get_inference_service
  service = get_inference_service()
  return service.predict_labels(text)


def process_comm_answer(answer_id: int, session_id: int, question_no: int, text: str):
  labels = _predict_comm_labels(text)

  save_chroma(
    answer_id=answer_id,
    session_id=session_id,
    question_no=question_no,
    text=text,
    labels=labels,
  )

  return {
    "transcript": text,
    "labels": labels,
  }
