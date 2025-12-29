from typing import List, Dict, Any
from app.database.schemas.interview import EvidenceSentence, SimilarAnswerLink


# ChromaDB에서 가져온 문장 데이터를 EvidenceSentence 스키마로 변환
def build_evidence_sentences(
        raw_sentences:List[Dict[str, Any]],
        limit:int=3
        )->List[EvidenceSentence]:
    filtered = [s for s in raw_sentences if str(s.get("text", "")).strip()]
    target = filtered if filtered else []

    return [
        EvidenceSentence(
            text=sent.get("text", ""),
            answer_id=sent.get("answer_id", 0),
            session_id=sent.get("session_id", 0)
        )
        for sent in target[-limit:]
    ]


# ChromaDB collection.query 결과를 SimilarAnswerLink 리스트로 변환
def build_similar_answer_links(
        chroma_query_result:dict,
        seen_ids:set=None,
        limit:int=2,
        similarity_threshold:float=0.5,
)->List[SimilarAnswerLink]:
    
    if seen_ids is None:
        seen_ids=set()

    links:List[SimilarAnswerLink]=[]

    ids = chroma_query_result.get("ids")
    if ids is None or len(ids)==0:
        return links
    
    for i in range(len(chroma_query_result["ids"][0])):
        meta=chroma_query_result["metadatas"][0][i]
        doc=chroma_query_result["documents"][0][i]
        distance=chroma_query_result["distances"][0][i]

        answer_id=meta.get("answer_id", 0)

        if answer_id in seen_ids:
            continue

        seen_ids.add(answer_id)

        similarity=round(1-distance, 3)

        if similarity>=similarity_threshold:
            text_preview=doc[:100]+"..." if len(doc)>100 else doc

            links.append(SimilarAnswerLink(
                answer_id=answer_id,
                text_preview=text_preview,
                similarity=similarity
            ))

        if len(links)>=limit:
            break

    return links

# ChromaDB 결과에서 문장 리스트 추출
def extract_chroma_sentences(
        chroma_get_result:dict,
)->List[Dict[str, Any]]:
    metas = chroma_get_result.get("metadatas")
    docs = chroma_get_result.get("documents")
    if metas is None or docs is None or len(metas)==0 or len(docs)==0:
        return []
    
    sentences=[]
    for meta, doc in zip(chroma_get_result["metadatas"], chroma_get_result["documents"]):
        sentences.append({
            "text":doc,
            "answer_id":meta.get("answer_id", 0),
            "session_id":meta.get("session_id", 0),
            "created_at":meta.get("created_at", 0)
        })


    return sentences
