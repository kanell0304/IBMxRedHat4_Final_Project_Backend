from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models.interview import Interview, InterviewAnswer
from app.database.schemas.interview import MetricChange, MetricChangeCardResponse
from app.service.copy_builder import build_metric_change_summary

# 지표 변화 분석
async def get_metric_changes(db:AsyncSession, user_id:int)->MetricChangeCardResponse:

    def is_korean(lang: str) -> bool:
        if lang is None:
            return True  # 기본값 ko
        lowered=str(lang).strip().lower()
        if lowered=="":
            return True
        return lowered.startswith("ko")

    # 1. 사용자의 모든 완료된 인터뷰 조회 후 한국어만 선별 (언어 비어 있으면 포함)
    stmt=(
        select(Interview)
        .where(Interview.user_id==user_id)
        .where(Interview.status==2)
        .order_by(Interview.created_at.asc())
    )
    result=await db.execute(stmt)
    all_interviews=result.scalars().all()
    interviews=[i for i in all_interviews if is_korean(getattr(i, "language", None))]
    if len(interviews)==0 and len(all_interviews)>0:
        interviews=all_interviews  # 언어값이 비어있는 경우 폴백

    total_interviews=len(interviews)


    if total_interviews<6:
        return MetricChangeCardResponse(
            total_interviews=total_interviews,
            has_enough_data=False,
            significant_changes=[],
            summary=f"총 {total_interviews}회 인터뷰 완료. 지표 비교를 위해 최소 6회 이상의 한국어 모의면접 데이터가 필요합니다."
        )

    # 2. 이전 3회와 최근 3회 분리
    previous_3=interviews[-6:-3]
    recent_3=interviews[-3:]

    # 3. 각 그룹 답변 수집
    previous_answers=[]
    for interview in previous_3:
        answers=await get_interview_answers(db, interview.i_id)
        previous_answers.extend(answers)

    recent_answers=[]
    for interview in recent_3:
        answers=await get_interview_answers(db, interview.i_id)
        recent_answers.extend(answers)

    # 4. 지표별 평균 계산
    previous_metrics=calculate_aggregate_metrics(previous_answers)
    recent_metrics=calculate_aggregate_metrics(recent_answers)

    # 5. 변화율 계산 및 필터링
    significant_changes=calculate_metric_changes(previous_metrics, recent_metrics)

    # 6. 요약 문장 생성
    summary=build_metric_change_summary(significant_changes, total_interviews)
    
    return MetricChangeCardResponse(
        total_interviews=total_interviews,
        has_enough_data=True,
        significant_changes=significant_changes,
        summary=summary
    )


# 인터뷰의 모든 답변 조회
async def get_interview_answers(db:AsyncSession, i_id:int)->List[InterviewAnswer]:
    stmt=(
        select(InterviewAnswer)
        .where(InterviewAnswer.i_id==i_id)
        .where(InterviewAnswer.deleted_at.is_(None))
    )
    result=await db.execute(stmt)
    return result.scalars().all()


# 답변들의 지표 평균 계산
def calculate_aggregate_metrics(answers:List[InterviewAnswer])->Dict[str, float]:

    metrics:Dict[str, List[float]]={
        "speech_rate_wpm":[],
        "pause_count":[],
        "silence_ratio":[],
        "avg_confidence":[],
    }

    bert_labels:Dict[str, List[float]]={}

    for answer in answers:
        # STT metrics 수집
        if answer.stt_metrics_json:
            stt=answer.stt_metrics_json
            if "speech_rate_wpm" in stt and stt["speech_rate_wpm"]:
                metrics["speech_rate_wpm"].append(float(stt["speech_rate_wpm"]))
            if "pause_count" in stt and stt["pause_count"] is not None:
                metrics["pause_count"].append(float(stt["pause_count"]))
            if "silence_ratio" in stt and stt["silence_ratio"] is not None:
                metrics["silence_ratio"].append(float(stt["silence_ratio"]))
            if "avg_confidence" in stt and stt["avg_confidence"]:
                metrics["avg_confidence"].append(float(stt["avg_confidence"]))

        # BERT labels 수집
        if answer.labels_json and "overall_labels" in answer.labels_json:
            labels=answer.labels_json["overall_labels"]
            for label_name, value in labels.items():
                if label_name not in bert_labels:
                    bert_labels[label_name]=[]
                # value가 dict이면 score 추출, 아니면 그대로 사용
                if isinstance(value, dict):
                    score=value.get("score", value.get("label", 0))
                else:
                    score=value
                bert_labels[label_name].append(float(score))

    # 평균 계산
    aggregated:Dict[str, float]={}

    # STT metrics 평균
    for key, values in metrics.items():
        if values:
            aggregated[key]=sum(values)/len(values)

    # BERT labels 평균
    for label_name, values in bert_labels.items():
        if values:
            aggregated[f"bert_{label_name}"]=sum(values)/len(values)

    return aggregated


# 지표 변화 계산 및 필터링
def calculate_metric_changes(
    previous:Dict[str, float],
    recent:Dict[str, float]
)->List[MetricChange]:
    
    changes:List[MetricChange]=[]

    # 공통 지표만 비교
    common_keys=set(previous.keys())&set(recent.keys())

    for key in common_keys:
        prev_val=previous[key]
        recent_val=recent[key]

        if prev_val==0:
            continue

        # 분모가 너무 작을 때 과도한 퍼센트가 나오지 않도록 보호
        denom = prev_val if abs(prev_val) >= 0.1 else 0.1
        change_percent=((recent_val-prev_val)/denom)*100
        # 100% 이상/이하로는 표시하지 않음
        if change_percent > 100:
            change_percent = 100
        if change_percent < -100:
            change_percent = -100

        if abs(change_percent)<10:
            continue

        # 방향 결정
        if change_percent>0:
            direction="up"
        elif change_percent<0:
            direction="down"
        else:
            direction="stable"

        # 긍정적 변화 판단
        is_positive=is_positive_change(key, direction)

        # 한글 이름 매핑
        metric_display_name=get_metric_display_name(key)

        changes.append(MetricChange(
            metric_name=metric_display_name,
            previous_avg=round(prev_val, 2),
            recent_avg=round(recent_val, 2),
            change_percent=round(change_percent, 1),
            direction=direction,
            is_positive=is_positive
        ))

    # 변화율이 큰 순으로 정렬
    changes.sort(key=lambda x: abs(x.change_percent), reverse=True)

    # 상위 5개만 반환
    return changes[:5]


# 긍정적 변화 판단
def is_positive_change(metric_key:str, direction:str)->bool:
    # 상승이 좋은 지표
    positive_on_up = ["speech_rate_wpm", "avg_confidence"]

    # 하락이 좋은 지표
    positive_on_down = ["pause_count", "silence_ratio"]

    if any(key in metric_key for key in positive_on_up):
        return direction == "up"
    if any(key in metric_key for key in positive_on_down):
        return direction == "down"
    # bert 라벨 점수는 낮을수록 좋음
    if "bert_" in metric_key:
        return direction == "down"
    # 알 수 없으면 상승을 개선으로 간주
    return direction == "up"


# 한글 지표 이름 매핑
def get_metric_display_name(key:str)->str:
    mapping = {
        "speech_rate_wpm":"발화 속도(WPM)",
        "pause_count":"침묵 횟수",
        "silence_ratio":"침묵 비율",
        "avg_confidence":"STT 신뢰도",
        "bert_slang":"비속어 사용",
        "bert_filler":"군말/망설임",
        "bert_biased":"편향적 표현",
        "bert_curse":"욕설 사용",
        "bert_formality_inconsistency":"격식 불일치",
        "bert_disfluency_repetition":"반복/더듬기",
        "bert_vague":"모호한 표현",
        "bert_ending_da":"'-다' 종결형",
    }
    return mapping.get(key, key.replace("bert_", "").replace("_", " ").title())
