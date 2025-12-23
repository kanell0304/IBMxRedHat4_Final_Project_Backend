import os
from typing import Dict, Any, List, Optional
from collections import defaultdict
from app.database.models.interview import InterviewAnswer, Interview
from app.infra.chroma_db import collection, get_embedding


# 여러 답변의 BERT labels 집계하여 interview 대표 라벨 산출
def aggregate_bert_labels(labels_list: List[Dict[str, int]])->Dict[str, Dict[str, Any]]:
    if not labels_list:
        return {}
    
    label_keys=labels_list[0].keys()
    aggregated={}

    for key in label_keys:
        values=[labels.get(key, 0) for labels in labels_list]
        count_ones=sum(values)

        avg_score=count_ones/len(values)

        final_label=1 if count_ones>len(values)/2 else 0

        aggregated[key]={
            "score":avg_score,
            "label":final_label,
        }

    return aggregated


# 텍스트를 임베딩하고 ChromaDB에 저장
# Chroma 메타데이터는 str/int/float/bool만 허용
def _flatten_labels(labels: Dict[str, Any]) -> Dict[str, Any]:
  flat_labels: Dict[str, Any] = {}  # chroma 메타데이터용 단순 키/값
  for key, value in labels.items():
    if isinstance(value, dict):
      score_val = value.get("score")  # 확률 값
      label_flag = value.get("label")  # 0/1 플래그
      if score_val is not None:
        flat_labels[f"{key}_score"] = float(score_val)
      if label_flag is not None:
        flat_labels[f"{key}_label"] = int(label_flag)
      continue
    flat_labels[key] = value if isinstance(value, (str, int, float, bool)) else str(value)
  return flat_labels


def save_chroma(
    answer_id: int,
    session_id: int,
    question_no: int,
    user_id: int,
    text: str,
    sentences: List[Dict[str, Any]],
    label_counts: Dict[str, int],
    overall_raw_labels: Dict[str, Any],
    stt_metrics: Optional[Dict[str, Any]] = None,
    created_at: Optional[float] = None,
):

  # user_id 추가 전 저장된 기존 문서가 있으면 제거하고 덮어씀
  try:
    collection.delete(where={"answer_id": answer_id})
  except Exception:
    pass

  # 1) 전체 transcript 문서
  full_embedding = get_embedding(text)
  flat_overall = _flatten_labels(overall_raw_labels)


  # stt_metrics 평탄화 작업
  flat_stt: Dict[str, Any]={}
  if stt_metrics:
    for key, value in stt_metrics.items():
      if isinstance(value, (int, float, str, bool)):
        flat_stt[f"stt_{key}"]=value


  full_metadata: Dict[str, Any] = {
    "type": "user_answer_full",
    "answer_id": answer_id,
    "session_id": session_id,
    "question_no": question_no,
    "user_id": user_id,
    "sentence_total": len(sentences),
    **{f"{k}_count": int(v) for k, v in label_counts.items()},
    **flat_overall,
    **flat_stt,
  }

  if created_at is not None:
    full_metadata["created_at"]=created_at

  ids: List[str] = [f"user_{user_id}_answer_{answer_id}_full"]
  docs: List[str] = [text]
  metas: List[Dict[str, Any]] = [full_metadata]
  embeds: List[List[float]] = [full_embedding]

  # 2) 문장 단위 문서
  for idx, sent in enumerate(sentences):
    sent_text = sent.get("text", "").strip()
    if not sent_text:
      continue
    sent_labels = sent.get("labels", {})
    sent_embedding = get_embedding(sent_text)
    sent_metadata: Dict[str, Any] = {
      "type": "user_answer_sentence",
      "answer_id": answer_id,
      "session_id": session_id,
      "question_no": question_no,
      "user_id": user_id,
      "sentence_index": idx,
      **{f"{k}_label": int(v) for k, v in sent_labels.items()},
    }

    if created_at is not None:
      sent_metadata["created_at"]=created_at
    ids.append(f"user_{user_id}_answer_{answer_id}_sent_{idx}")
    docs.append(sent_text)
    metas.append(sent_metadata)
    embeds.append(sent_embedding)

  # 저장
  collection.add(
    ids=ids,
    documents=docs,
    metadatas=metas,
    embeddings=embeds,
  )


# STT 결과에서 transcript만 모아 한 문장으로 합침
def extract_transcript(stt_result: Dict[str, Any]) -> str:
  transcripts: List[str] = []
  for item in stt_result.get("results", []):
    for alt in item.get("alternatives", []):
      text = alt.get("transcript")
      if text:
        transcripts.append(text.strip())
  if not transcripts:
    raise ValueError("transcript 없음")
  return " ".join(transcripts)


def _i_predict_labels(text: str) -> Dict[str, Any]:
  from app.service.i_bert_service import get_inference_service

  service = get_inference_service()
  return service.predict_labels(text)


def _labels_only(raw: Dict[str, Any]) -> Dict[str, int]:
  return {k: int(v.get("label", 0)) for k, v in raw.items()}


def _split_sentences(text: str) -> List[str]:
  sentences: List[str] = []
  current: List[str] = []

  for char in text.strip():
    current.append(char)
    if char in ".?!":
      sentence = "".join(current).strip()
      if sentence:
        sentences.append(sentence)
      current = []
  tail = "".join(current).strip()
  if tail:
    sentences.append(tail)
  return sentences


async def i_process_answer(answer_id: int, db):
  answer: InterviewAnswer | None = await db.get(InterviewAnswer, answer_id)
  if not answer:
    raise ValueError("해당 answer_id를 찾을 수 없습니다.")
  interview: Interview | None = await db.get(Interview, answer.i_id)
  if not interview:
    raise ValueError("해당 인터뷰 정보를 찾을 수 없습니다.")
  
  # 기존 계산값 재사용
  transcript = answer.transcript 
  stt_metrics=answer.stt_metrics_json

  if not transcript:
    raise ValueError("transcript가 없습니다.")
  if not stt_metrics:
    raise ValueError("stt_metrics가 없습니다.")

  sentences = _split_sentences(transcript)
  if not sentences:
    sentences = [transcript]

  # 전체/문장별 라벨
  overall_raw = _i_predict_labels(transcript)
  overall_labels = _labels_only(overall_raw)

  sentence_entries: List[Dict[str, Any]] = []
  for s in sentences:
    raw = _i_predict_labels(s)
    labels_only=_labels_only(raw)
    sentence_entries.append({
      "text": s,
      "labels": labels_only,
    })

  # 문장별 라벨
  label_counts = {k: 0 for k in overall_labels.keys()}
  for sent in sentence_entries:
    for k, v in sent["labels"].items():
      if v:
        label_counts[k] += 1

  # mysql에 올리기
  answer.transcript = transcript
  answer.labels_json = {
    "overall_labels": overall_labels,
    "sentences": [
      {"text": s["text"], "labels": s["labels"]}
      for s in sentence_entries
    ],
    "label_counts": label_counts,
  }
  answer.stt_metrics_json=stt_metrics
  await db.commit()
  await db.refresh(answer)

  
  save_chroma(
    answer_id=answer.i_answer_id,
    session_id=answer.i_id,
    question_no=answer.q_order or 0,
    user_id=interview.user_id,
    text=transcript,
    sentences=sentence_entries,
    label_counts=label_counts,
    overall_raw_labels=overall_raw,
    stt_metrics=stt_metrics,
    created_at=answer.created_at.timestamp() if answer.created_at else None,
  )

  return {
    "transcript": transcript,
    "sentences": [
      {"text": s["text"], "labels": s["labels"]}
      for s in sentence_entries
    ],
    "label_counts": label_counts,
    "stt_metrics": stt_metrics,
  }