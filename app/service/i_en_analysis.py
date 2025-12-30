from typing import Dict, Any
from app.service.llm_service import OpenAIService
from app.prompts.interview_prompts_english import build_english_interview_prompt, ENGLISH_SYSTEM_MESSAGE
import json


def calculate_grade(score: int) -> str:
    if score >= 90:
        return "S"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


async def analyze_english_interview(
        transcript:str,
        stt_metrics:Dict[str, Any],
        qa_list:list
)->Dict[str, Any]:

    llm_service=OpenAIService()

    speech_rate=float(stt_metrics.get("speech_rate", 0.0) or 0.0)
    pause_ratio=float(stt_metrics.get("pause_ratio", 0.0) or 0.0)

    filler_hard=0
    filler_soft=0
    filler_obj=stt_metrics.get("filler")
    if isinstance(filler_obj, dict):
        filler_hard=int(filler_obj.get("hard", 0) or 0)
        filler_soft=int(filler_obj.get("soft", 0) or 0)
    else:
        filler_hard=int(stt_metrics.get("filler_count", 0) or 0)

    prompt=build_english_interview_prompt(
        transcript=transcript,
        stt_metrics=stt_metrics,
        qa_list=qa_list
    )

    response=await llm_service.client.chat.completions.create(
        model=llm_service.model,
        messages=[
            {"role": "system", "content": ENGLISH_SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    content=response.choices[0].message.content or "{}"
    try:
        result=json.loads(content)
    except json.JSONDecodeError:
        result={}

    score_value = result.get("score", 70)

    return {
        "score":score_value,
        "grade":calculate_grade(score_value),
        "comments":result.get(
            "comments",
            [
                "답변의 구조와 논리성은 갖추었으나 구체적인 예시가 부족합니다.",
                f"발화 속도 {speech_rate:.0f} WPM, 침묵 비율 {pause_ratio:.0%}, hard filler {filler_hard}회로 전달력은 평균 수준입니다.",
                "전반적으로 이해 가능한 답변이지만 더 많은 연습이 필요합니다.",
            ],
        ),
        "improvements":result.get(
            "improvements",
            [
                "STAR 기법(Situation-Task-Action-Result)을 사용하여 답변에 구조를 부여하고 구체적인 사례를 포함하세요.",
                "발화 전 2-3초 멈추고 답변의 핵심 포인트 3가지를 먼저 정리한 뒤 말하는 연습을 하세요.",
                "Hard filler(uh, um) 대신 짧은 침묵을 활용하고, 140-160 WPM 속도를 유지하는 연습을 하세요.",
            ],
        ),
        "stt_metrics":stt_metrics,
    }