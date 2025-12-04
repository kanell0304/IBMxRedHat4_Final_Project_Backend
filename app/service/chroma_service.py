import os
from typing import Dict, Any, List, Optional
from app.core.settings import settings
from app.database.models.interview import InterviewAnswer
from app.infra.chroma_db import collection, get_embedding
from collections import defaultdict



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
    labels: Dict[str, Any]):
  
  embedding = get_embedding(text)  # 텍스트를 숫자로 임베딩

  metadata = {
    "type": "user_answer",
    "answer_id": answer_id, # DB 답변 ID (추적용)
    "session_id": session_id, # 같은 인터뷰 세션 묶음 식별
    "question_no": question_no,
    "user_id": user_id,
    **_flatten_labels(labels), # BERT 결과를 평탄화해 저장
  }

  # 벡터, 원문, 메타데이터를 한 묶음으로 collection에 저장
  collection.add(
    ids=[f"user_{user_id}_answer_{answer_id}"], # 고유 ID로 재검색 시 바로 특정
    documents=[text],# 검색 결과로 보여줄 실제 답변 텍스트
    metadatas=[metadata],
    embeddings=[embedding], # 유사도 검색의 핵심 데이터
  )


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


def _i_predict_labels(text: str) -> Dict[str, Any]:
  from app.service.i_bert_service import get_inference_service
  service = get_inference_service()
  return service.predict_labels(text)


async def i_process_answer(answer_id: int, db):
  answer: InterviewAnswer | None = await db.get(InterviewAnswer, answer_id)
  if not answer:
    raise ValueError("해당 answer_id를 찾을 수 없습니다.")
  transcript = answer.transcript  # 기존 STT 결과가 있으면 재사용


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



# Retrieve 함수
# 약점 패턴 발견
def analyze_weakness_patterns(user_id:int)->Dict[str, Any]:

  all_answers=collection.get(
    where={"user_id":user_id}
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

  for metadata in all_answers["metadata"]:
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
    pattern_summary=f"{top_label}이(가) {top_count}개 질문에서 반복적으로 나타납니다.)"
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
  
  where_condition={"user_id":user_id}
  if question_no is not None:
    where_condition={
      "$and":[
        {"user_id":user_id},
        {"question_no":question_no}
      ]
    }
  
  results=collection.get(where=where_condition)

  if not results["ids"]:
    return {
      "timeline":[],
      "improvement_rate":0.0,
      "evolution_summary":"분석할 데이터가 부족합니다."
    }
  
  
  session_data=defaultdict(lambda:{
    "score":[],
    "issue_count":0,
    "answer_ids":[]
  })

  for metadata in results["metadatas"]:
    session_id=metadata.get("session_id",0)

    scores=[]

    for key, value in metadata.items():
      if key.endswith("_score"):
        scores.append(float(value))
      if key.endswith("_label") and value==1:
        session_data[session_id]["issue_count"]+=1

    if scores:
      session_data[session_id]["scores"].extend(scores)
      session_data[session_id]["answer_ids"].append(metadata.get("answer_id"))

  timeline=[]
  for session_id, data in sorted(session_data.items()):
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
      "improvement_rate":0.0,
      "evolution_summary":"비교할 데이터가 부족합니다. 더 연습해보세요!"
    }
  
  first_score=timeline[0]["avg_score"]
  last_score=timeline[-1]["avg_score"]
  improvement_rate=((last_score-first_score)/first_score*100) if first_score>0 else 0.0

  best_session=min(timeline, key=lambda x:x["avg_score"])
  worst_session=max(timeline, key=lambda x:x["avg_score"])

  if improvement_rate<-10:
    evolution_summary=f"평균 점수가 {first_score:.2f} → {last_score:.2f}로 {abs(improvement_rate):.0f}% 개선!"
  elif improvement_rate>10:
    evolution_summary=f"최근 점수가 높아졌습니다. 초심으로 돌아가볼까요?"
  else:
    evolution_summary=f"일관된 실력을 유지중입니다."

  return {
    "timeline":timeline,
    "improvement_rate":round(improvement_rate, 2),
    "best_session":best_session["session_id"],
    "worst_session":worst_session["session_id"],
    "evolution_summary":evolution_summary,
    "first_avg":round(first_score, 2),
    "recent_avg":round(last_score, 2)
  }


