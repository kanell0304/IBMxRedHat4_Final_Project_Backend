from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.schemas.interview import WeaknessCardResponse, WeaknessDetail, EvidenceSentence, SimilarAnswerLink
from app.database.crud import interview as crud
from app.infra.chroma_db import collection
from app.service.evidence_builder import build_evidence_sentences, build_similar_answer_links, extract_chroma_sentences
from app.service.copy_builder import build_improvement_guide, build_weakness_summary, get_label_display_name

def _top_sentences_by_frequency(sentences: List[Dict[str, Any]], limit: int = 3) -> List[EvidenceSentence]:
    # 텍스트가 비어있는 문장은 제외
    valid = [s for s in sentences if str(s.get("text", "")).strip()]
    if not valid:
        return []
    # 텍스트별 빈도 계산
    freq_map: Dict[str, Dict[str, Any]] = {}
    for s in valid:
        text = s.get("text", "").strip()
        freq_map.setdefault(text, {"count": 0, "latest": 0, "sample": s})
        freq_map[text]["count"] += 1
        freq_map[text]["latest"] = max(freq_map[text]["latest"], s.get("created_at", 0) or 0)
    # 빈도 우선, 최신순 정렬
    top_texts = sorted(
        freq_map.items(),
        key=lambda x: (x[1]["count"] * -1, -x[1]["latest"])
    )[:limit]
    top_sentences: List[EvidenceSentence] = []
    for text, meta in top_texts:
        sample = meta["sample"]
        top_sentences.append(
            EvidenceSentence(
                text=f"{text} (총 {meta['count']}회)",
                answer_id=sample.get("answer_id", 0),
                session_id=sample.get("session_id", 0)
            )
        )
    return top_sentences

def _build_trend_text(sentences: List[Dict[str, Any]]) -> str:
    if not sentences:
        return ""
    with_timestamp=[s for s in sentences if s.get("created_at")]
    if not with_timestamp:
        return ""
    sorted_s=sorted(with_timestamp, key=lambda x: x.get("created_at", 0))
    mid=max(1, len(sorted_s)//2)
    earlier=sorted_s[:mid]
    recent=sorted_s[mid:]
    earlier_cnt=len(earlier)
    recent_cnt=len(recent)
    if earlier_cnt==0 and recent_cnt>0:
        return "최근에 새로 발생하기 시작했습니다."
    change=recent_cnt - earlier_cnt
    if earlier_cnt==0:
        pct_change=0
    else:
        pct_change=change/earlier_cnt
    if pct_change > 0.2:
        return f"최근 발생 빈도가 늘어나는 추세입니다.(+{change}회)"
    if pct_change < -0.2:
        return f"최근 발생 빈도가 줄어드는 추세입니다.({abs(change)}회 감소)"
    return "최근 발생 빈도가 비슷하게 유지되고 있습니다."

# 말버릇/약점 분석
async def get_weakness_analysis(db:AsyncSession, user_id:int)->WeaknessCardResponse:

    def is_korean(lang: str) -> bool:
        if lang is None:
            return True  # 기본값이 ko인 경우도 포함
        lowered = str(lang).strip().lower()
        if lowered == "":
            return True
        return lowered.startswith("ko")

    interviews=await crud.list_i(db, user_id)
    korean_interviews=[i for i in interviews if is_korean(getattr(i, "language", None))]
    if len(korean_interviews)==0 and len(interviews)>0:
        korean_interviews=interviews  # 언어값 비어있는 경우까지 포함
    total_interviews=len(korean_interviews)

    # 3회 미만 데이터 부족
    if total_interviews<3:
        return WeaknessCardResponse(
            total_interviews=total_interviews,
            has_enough_data=False,
            top_weaknesses=[],
            summary=f"총 {total_interviews}회 인터뷰 완료. 약점 분석을 위해 최소 3회 이상의 한국어 모의면접 데이터가 필요합니다."
        )

    try:
        # ChromaDB에서 사용자의 문장 조회 (언어 필터 제거해 None/ko-KR 등 모든 데이터 포함)
        results=collection.get(
            where={
                "$and":[
                    {"user_id":user_id},
                    {"type":"user_answer_sentence"},
                ]
            },
            include=["metadatas", "documents"]
        )

        ids = results.get("ids")
        metas = results.get("metadatas")
        if ids is None:
            ids=[]
        if metas is None:
            metas=[]
        if len(ids)==0 or len(metas)==0:
            return WeaknessCardResponse(
                total_interviews=total_interviews,
                has_enough_data=True,
                top_weaknesses=[],
                summary="분석할 문장을 찾지 못했습니다. 다음 면접 이후 다시 시도해주세요."
            )
        
        # ChromaDB 결과를 표준 포맷으로 변환
        all_sentences=extract_chroma_sentences(results)

        # created_at으로 정렬
        sorted_sentences=sorted(all_sentences, key=lambda x:x.get("created_at", 0))

        # 라벨별 문장 수집
        label_data:Dict[str, List[Dict[str, Any]]]={}


        for sent in sorted_sentences:
            idx=all_sentences.index(sent)
            if idx >= len(metas):
                continue
            meta=metas[idx]

            for key, value in meta.items():
                if not key.endswith("_label"):
                    continue

                # value가 배열/numpy 타입인 경우 첫 원소만 사용
                if hasattr(value, "tolist"):
                    value=value.tolist()
                if isinstance(value, (list, tuple)) and len(value)>0:
                    value=value[0]

                try:
                    is_positive = float(value)==1
                except Exception:
                    is_positive = False

                if is_positive:
                    label_name=key.replace("_label", "")

                    if label_name not in label_data:
                        label_data[label_name]=[]
                    
                    label_data[label_name].append(sent)


        # 라벨별 발생 횟수로 정렬하여 TOP 3 선택
        label_counts={label:len(sentences) for label, sentences in label_data.items()}
        if len(label_counts)==0:
            return WeaknessCardResponse(
                total_interviews=total_interviews,
                has_enough_data=True,
                top_weaknesses=[],
                summary="분석할 문장을 찾지 못했습니다. 다음 면접 이후 다시 시도해주세요."
            )
        top_3_labels=sorted(label_counts.items(), key=lambda x:x[1], reverse=True)[:3]


        # 각 약점에 대한 상세 정보 생성
        top_weaknesses:List[WeaknessDetail]=[]

        for label_name, count in top_3_labels:
            sentences=label_data[label_name]

            # 가장 많이 나온 문장 TOP3
            evidence_sentences=_top_sentences_by_frequency(sentences, limit=3)

            similar_answers=await find_similar_answers_for_label(
                user_id=user_id,
                label_name=label_name,
                limit=2
            )

            avg_score=await calculate_label_avg_score(user_id, label_name)

            top_weaknesses.append(WeaknessDetail(
                label_name=label_name,
                label_display_name=get_label_display_name(label_name),
                avg_score=round(avg_score, 2),
                occurrence_count=count,
                evidence_sentences=evidence_sentences,
                similar_answers=similar_answers,
                improvement_guide=build_improvement_guide(label_name)
            ))

        # 요약 문장 생성
        # 최고 약점에 대한 추세 설명 추가
        top_label_name=top_weaknesses[0].label_name if top_weaknesses else ""
        top_trend=""
        if top_label_name and top_label_name in label_data:
            top_trend=_build_trend_text(label_data[top_label_name])

        summary=build_weakness_summary(top_weaknesses, total_interviews, top_trend=top_trend)

        return WeaknessCardResponse(
            total_interviews=total_interviews,
            has_enough_data=True,
            top_weaknesses=top_weaknesses,
            summary=summary
        )
    except Exception as e:
        # 오류가 나더라도 충분한 인터뷰 횟수가 있으면 최소 메시지라도 보여줌
        return WeaknessCardResponse(
            total_interviews=total_interviews,
            has_enough_data=True,
            top_weaknesses=[],
            summary=f"분석 중 오류가 발생했습니다. 다음 면접 후 다시 시도해주세요. ({e})"
        )


# 특정 라벨에 대한 유사 답변 찾기
async def find_similar_answers_for_label(
    user_id:int,
    label_name:str,
    limit:int=2
)->List[SimilarAnswerLink]:

    # 해당 라벨이 있는 문장들 조회
    label_sentences=collection.get(
        where={
            "$and":[
                {"user_id":user_id},
                {"type":"user_answer_sentence"},
                {f"{label_name}_label":1}
            ]
        },
        include=["metadatas", "embeddings", "documents"],
        limit=5
    )

    embeddings = label_sentences.get("embeddings")
    if embeddings is None:
        embeddings=[]
    if len(embeddings)==0:
        return []

    query_embedding=embeddings[0]

    similar_results=collection.query(
        query_embeddings=[query_embedding],
        n_results=limit+5,
        where={
            "$and":[
                {"user_id":user_id},
                {"type":"user_answer_full"}
            ]
        }
    )

    return build_similar_answer_links(
        similar_results,
        seen_ids=set(),
        limit=limit,
        similarity_threshold=0.5
    )


# 라벨의 평균 스코어 계산
async def calculate_label_avg_score(user_id: int, label_name: str) -> float:

    results=collection.get(
        where={
            "$and":[
                {"user_id":user_id},
                {"type":"user_answer_full"}
            ]
        },
        include=["metadatas"]
    )

    scores:List[float]=[]

    metas = results.get("metadatas")
    if metas is None:
        metas=[]

    for meta in metas:
        score_key=f"{label_name}_score"
        if score_key in meta:
            scores.append(float(meta[score_key]))

    if not scores:
        return 0.0

    return sum(scores)/len(scores)
