from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.schemas.interview import ImmediateResultResponse, QuestionDetailEvaluation, SimilarAnswerHint, I_Report
from app.infra.chroma_db import collection
from app.database.crud import interview as crud
from app.service.copy_builder import build_similar_answer_hint_message



# 인터뷰 직후 결과 조회 (총평 + 질문별 평가 + 유사답변 힌트)
async def get_immediate_result(i_id:int, db:AsyncSession)->ImmediateResultResponse:

    # 1. 인터뷰 총평 조회 (scope=overall)
    overall_result=await crud.get_result_by_scope(db, i_id, scope="overall")
    if not overall_result:
        raise ValueError("인터뷰 총평이 아직 생성되지 않았습니다.")

    overall_report=I_Report(**overall_result.report)

    # 2. 질문별 세부 평가 조회 (scope=per_question)
    per_question_results=await crud.get_results_by_scope(db, i_id, scope="per_question")

    question_details:List[QuestionDetailEvaluation]=[]
    for result in per_question_results:
        report_data=result.report

        # 답변 원문 조회
        if result.i_answer_id:
            answer=await crud.get_answer(db, result.i_answer_id)
            user_answer=answer.transcript if answer else ""
        else:
            user_answer = ""

        question_details.append(QuestionDetailEvaluation(
            q_index=report_data.get("q_index", 0),
            q_text=report_data.get("q_text", ""),
            user_answer=user_answer,
            question_intent=report_data.get("question_intent", "질문 의도를 분석 중입니다."),
            is_appropriate=report_data.get("is_appropriate", True),
            feedback=report_data.get("suggestion", ""),
            evidence_sentences=report_data.get("evidence_sentences", [])
        ))

    # 3. 유사 답변 힌트 (3회 이상일 때만)
    interview=await crud.get_i(db, i_id)
    similar_hint=await find_similar_answer_hint(db, interview.user_id, i_id)

    return ImmediateResultResponse(
        i_id=i_id,
        overall_report=overall_report,
        question_details=question_details,
        similar_hint=similar_hint
    )


# 유사 답변 힌트 찾기 (ChromaDB, 3회 이상일 때만)
async def find_similar_answer_hint(
    db:AsyncSession,
    user_id:int,
    current_i_id:int
)->Optional[SimilarAnswerHint]:

    # 사용자의 총 인터뷰 수 확인
    all_interviews=await crud.list_i(db, user_id)
    if len(all_interviews)<3:
        return None

    # 현재 인터뷰의 답변들 가져오기
    current_interview=await crud.get_i(db, current_i_id)
    current_answers=current_interview.answers

    if not current_answers:
        return None

    # 현재 인터뷰의 첫 번째 답변으로 유사도 검색
    current_answer=current_answers[0]

    # ChromaDB에서 현재 답변의 임베딩 가져오기
    current_doc_id=f"user_{user_id}_answer_{current_answer.i_answer_id}_full"

    try:
        current_data=collection.get(
            ids=[current_doc_id],
            include=["embeddings"]
        )

        if not current_data["embeddings"] or len(current_data["embeddings"])==0:
            return None

        current_embedding=current_data["embeddings"][0]

        # 유사한 과거 답변 검색 (자기 자신 제외)
        similar_results=collection.query(
            query_embeddings=[current_embedding],
            n_results=5,  # 상위 5개 가져와서 현재 세션 제외
            where={
                "$and": [
                    {"user_id": user_id},
                    {"type": "user_answer_full"}
                ]
            }
        )

        # 현재 인터뷰 세션 제외하고 가장 유사한 답변 찾기
        for i in range(len(similar_results["ids"][0])):
            meta=similar_results["metadatas"][0][i]
            session_id=meta.get("session_id", 0)
            answer_id=meta.get("answer_id", 0)

            # 현재 인터뷰가 아닌 경우
            if session_id!=current_i_id:
                distance=similar_results["distances"][0][i]
                similarity=round(1 - distance, 3)

                # 유사도가 0.7 이상일 때만 힌트 제공
                if similarity>=0.7:
                    
                    message=build_similar_answer_hint_message(similarity)

                    return SimilarAnswerHint(
                        message=message,
                        answer_id=answer_id,
                        similarity=similarity
                    )

        return None

    except Exception:
        return None
