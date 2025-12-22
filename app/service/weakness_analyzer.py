from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.schemas.interview import WeaknessCardResponse, WeaknessDetail, EvidenceSentence, SimilarAnswerLink
from app.database.crud import interview as crud
from app.infra.chroma_db import collection
from app.service.evidence_builder import build_evidence_sentences, build_similar_answer_links, extract_chroma_sentences
from app.service.copy_builder import build_improvement_guide, build_weakness_summary, get_label_display_name


# 말버릇/약점 분석
async def get_weakness_analysis(db:AsyncSession, user_id:int)->WeaknessCardResponse:

    interviews=await crud.list_i(db, user_id)
    total_interviews=len(interviews)

    # 3회 미만 데이터 부족
    if total_interviews<3:
        return WeaknessCardResponse(
            total_interviews=total_interviews,
            has_enough_data=False,
            top_weaknesses=[],
            summary=f"총 {total_interviews}회 인터뷰 완료. 약점 분석을 위해 최소 3회 이상의 모의면접 데이터가 필요합니다."
        )

    # ChromaDB에서 사용자의 모든 문장 조회
    results=collection.get(
        where={
            "$and":[
                {"user_id":user_id},
                {"type":"user_answer_sentence"}
            ]
        },
        include=["metadatas", "documents"]
    )

    if not results["ids"] or not results["metadatas"]:
        return WeaknessCardResponse(
            total_interviews=total_interviews,
            has_enough_data=False,
            top_weaknesses=[],
            summary="분석할 데이터가 없습니다."
        )
    
    # ChromaDB 결과를 표준 포맷으로 변환
    all_sentences=extract_chroma_sentences(results)

    # created_at으로 정렬
    sorted_sentences=sorted(all_sentences, key=lambda x:x.get("created_at", 0))

    # 라벨별 문장 수집
    label_data:Dict[str, List[Dict[str, Any]]]={}


    for sent in sorted_sentences:
        idx=all_sentences.index(sent)
        meta=results["metadatas"][idx]

        for key, value in meta.items():
            if key.endswith("_label") and value==1:
                label_name=key.replace("_label", "")

                if label_name not in label_data:
                    label_data[label_name]=[]
                
                label_data[label_name].append(sent)


    # 라벨별 발생 횟수로 정렬하여 TOP 3 선택
    label_counts={label:len(sentences) for label, sentences in label_data.items()}
    top_3_labels=sorted(label_counts.items(), key=lambda x:x[1], reverse=True)[:3]


    # 각 약점에 대한 상세 정보 생성
    top_weaknesses:List[WeaknessDetail]=[]

    for label_name, count in top_3_labels:
        sentences=label_data[label_name]

        # 증거 문장 2~3개 선택(최신순)
        evidence_sentences=build_evidence_sentences(sentences, limit=3)

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
    summary=build_weakness_summary(top_weaknesses, total_interviews)

    return WeaknessCardResponse(
        total_interviews=total_interviews,
        has_enough_data=True,
        top_weaknesses=top_weaknesses,
        summary=summary
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

    if not label_sentences["embeddings"] or len(label_sentences["embeddings"])==0:
        return []

    query_embedding=label_sentences["embeddings"][0]

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

    for meta in results["metadatas"]:
        score_key=f"{label_name}_score"
        if score_key in meta:
            scores.append(float(meta[score_key]))

    if not scores:
        return 0.0

    return sum(scores)/len(scores)


