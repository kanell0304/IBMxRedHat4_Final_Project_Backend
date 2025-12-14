import os
from typing import Dict, Any, List, Optional
from collections import defaultdict
from app.core.settings import settings
from app.database.models.interview import InterviewAnswer, Interview
from app.infra.chroma_db import collection, get_embedding
from app.service.i_stt_metrics import compute_stt_metrics

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
):

  # user_id 추가 전 저장된 기존 문서가 있으면 제거하고 덮어쓴다 (answer_id 기준)
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

  # chromadb 저장
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



# Retrieve 함수
# 약점 패턴 발견
def analyze_weakness_patterns(user_id:int)->Dict[str, Any]:

  all_answers=collection.get(
    where={
      "$and":[
        {"user_id":user_id},
        {"type":"user_answer_sentence"}
      ]
    }
  )

  if not all_answers["ids"]:
    return {
      "weak_labels":[],
      "weak_questions":[],
      "label_details":{},
      "pattern_summary":"분석할 데이터가 부족합니다."
    }
  

  label_issues=defaultdict(list)
  question_issues_count=defaultdict(int)

  for metadata in all_answers["metadatas"]:
    q_no=metadata.get("question_no", 0)

    # 라벨 1인 항목 찾기
    for key, value in metadata.items():
      if key.endswith("_label") and value==1:
        label_name=key.replace("_label","")
        label_issues[label_name].append(q_no)
        question_issues_count[q_no]+=1
        
  # 사용자의 발화에서 가장 문제되는 라벨(상위 3개)
  weak_labels=sorted(
    label_issues.items(),
    key=lambda x:len(x[1]),
    reverse=True
  )[:3]

  # 문제 많은 질문(상위 3개)
  weak_questions=sorted(
    question_issues_count.items(),
    key=lambda x:x[1],
    reverse=True
  )[:3]


  # 패턴 요약 생성
  if weak_labels:
    top_label=weak_labels[0][0].replace("_"," ")
    top_count=len(set(weak_labels[0][1]))
    pattern_summary=f"{top_label}이(가) {top_count}개 질문에서 반복적으로 나타납니다."
  else:
    pattern_summary="특별한 약점 패턴이 발견되지 않았습니다."
  
  return {
    "weak_labels":[label for label, _ in weak_labels],
    "weak_questions":[q for q, _ in weak_questions],
    "label_details":{
      label:sorted(list(set(qnos)))
      for label, qnos in weak_labels
    },
    "pattern_summary":pattern_summary
  }

# 사용자 답변 스타일 개선현황 분석
def analyze_speech_style_evolution(
    user_id:int, question_no:Optional[int]=None
)->Dict[str, Any]:
  
  if question_no is None:
    where_condition:Dict[str, Any]={
      "$and":[
        {"user_id":user_id},
        {"type":"user_answer_full"},
      ]
    }
  
  else:
    where_condition={
      "$and":[
        {"user_id":user_id},
        {"type":"user_answer_full"},
        {"question_no":question_no},
      ]
    }
  
  results=collection.get(where=where_condition)

  if not results["ids"]:
    return {
      "timeline":[],
      "improvement_rate":0.0,
      "evolution_summary":"분석할 데이터가 부족합니다."
    }
  
  # 세션별 집계
  session_data=defaultdict(lambda:{
    "scores":[],
    "issue_count":0,
    "answer_ids":[]
  })

  for metadata in results["metadatas"]:
    session_id=metadata.get("session_id",0)

    scores:List[float]=[]

    for key, value in metadata.items():
      if key.endswith("_score"):
        scores.append(float(value))
      if key.endswith("_label") and value==1:
        session_data[session_id]["issue_count"]+=1

    if scores:
      session_data[session_id]["scores"].extend(scores)
      session_data[session_id]["answer_ids"].append(metadata.get("answer_id"))

  # 타임라인 정리 : session_id 오름차순
  timeline:List[Dict[str, Any]]=[]

  for session_id, data in sorted(session_data.items(), key=lambda x:x[0]):
    avg_score=sum(data["scores"])/len(data["scores"]) if data["scores"] else 0
    timeline.append({
      "session_id":session_id,
      "avg_score":round(avg_score, 2),
      "issue_count":data["issue_count"],
      "num_answers":len(data["answer_ids"])
    })

  if len(timeline)<2:
    return {
      "timeline":timeline,
      "improvement":{
        "direction":"same",
        "percent":0.0,
        "from":timeline[0]["avg_score"] if timeline else 0,
        "to":timeline[-1]["avg_score"] if timeline else 0,
        "summary":"비교할 데이터가 부족합니다. 더 연습해보세요!"
      }
    }
  
  first_score=timeline[0]["avg_score"]
  last_score=timeline[-1]["avg_score"]
 
  # 퍼센트 변화율 계산(항상 양수값으로)
  if first_score>0:
    percent=abs(last_score-first_score)/first_score*100
  else:
    percent=0.0
  
  # 방향 판단
  if last_score<first_score:
    direction="improved"
    summary=f"{percent:.1f}% 개선되었습니다."
  elif last_score>first_score:
    direction="worsened"
    summary=f"{percent:.1f}% 악화되었습니다."
  else:
    direction="same"
    summary="큰 변화 없이 일정한 실력을 유지하고 있습니다."
  
  return {
    "timeline":timeline,
    "improvement":{
      "direction":direction,
      "percent":round(percent, 2),
      "from":round(first_score, 2),
      "to":round(last_score, 2),
      "summary":summary,
    }
  }