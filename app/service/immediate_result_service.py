from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.schemas.interview import ImmediateResultResponse, QuestionDetailEvaluation, SimilarAnswerHint, I_Report
from app.infra.chroma_db import collection
from app.database.crud import interview as crud
from app.service.copy_builder import build_similar_answer_hint_message



# 인터뷰 직후 결과 조회 (총평 + 질문별 평가 + 유사답변 힌트)
async def get_immediate_result(i_id:int, db:AsyncSession)->ImmediateResultResponse:

    interview=await crud.get_i(db, i_id)
    if not interview:
        raise ValueError("인터뷰를 찾을 수 없습니다.")

    language=interview.language or 'ko'

    overall_result=await crud.get_result_by_scope(db, i_id, scope="overall")
    if not overall_result:
        raise ValueError("인터뷰 총평이 아직 생성되지 않았습니다.")

    if language == 'en':
        from app.database.schemas.interview import I_Report_En
        overall_report=I_Report_En(**overall_result.report)
    else:
        overall_report=I_Report(**overall_result.report)

    question_details:List[QuestionDetailEvaluation]=[]

    # DB의 모든 답변을 가져오기 (transcript가 있는 것만)
    valid_answers = [a for a in interview.answers if a.transcript and a.transcript.strip()]

    # LLM 평가와 매칭하기 위한 딕셔너리
    llm_evaluations = {}
    if hasattr(overall_report, 'content_per_question') and overall_report.content_per_question:
        for per_q in overall_report.content_per_question:
            llm_evaluations[per_q.q_index] = per_q

    # DB 답변 기준으로 질문별 평가 생성
    for answer in sorted(valid_answers, key=lambda a: a.q_order):
        question = None
        if answer.q_id:
            question = await crud.get_question(db, answer.q_id)

        # LLM 평가가 있으면 사용, 없으면 기본값
        llm_eval = llm_evaluations.get(answer.q_order)

        if llm_eval:
            question_details.append(QuestionDetailEvaluation(
                q_index=answer.q_order,
                q_text=llm_eval.q_text,
                user_answer=answer.transcript or "",
                question_intent=llm_eval.question_intent,
                is_appropriate=llm_eval.is_appropriate,
                feedback=llm_eval.suggestion,
                evidence_sentences=llm_eval.evidence_sentences
            ))
        else:
            # LLM 평가가 없는 경우 기본값
            question_details.append(QuestionDetailEvaluation(
                q_index=answer.q_order,
                q_text=question.question_text if question else "",
                user_answer=answer.transcript or "",
                question_intent="",
                is_appropriate=False,
                feedback="평가가 생성되지 않았습니다.",
                evidence_sentences=[]
            ))

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

        # 유사한 과거 답변 검색
        similar_results=collection.query(
            query_embeddings=[current_embedding],
            n_results=5,  # 상위 5개 가져와서 현재 세션 제외
            where={
                "$and": [
                    {"user_id": user_id},
                    {"type": "user_answer_full"},
                    {"language": current_interview.language or "ko"}
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
