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
                "내용은 전반적으로 무난하지만 핵심 메시지와 근거 예시가 더 필요합니다.",
                f"말하기 속도 {speech_rate:.0f} WPM, 침묵 비율 {pause_ratio:.0%}, hard filler {filler_hard}회로 유창성은 보통 수준입니다.",
                "전반적으로 안정적인 답변이지만 구체성을 높이면 더욱 좋습니다.",
            ],
        ),
        "improvements":result.get(
            "improvements",
            [
                "답변을 2~3개의 포인트로 먼저 구조화한 뒤, 각 포인트마다 1개의 구체 예시를 붙이는 연습을 하세요.",
                "말하기 전 2~3초 멈추고 답변 구조를 머릿속으로 정리한 뒤 시작하세요.",
            ],
        ),
        "stt_metrics":stt_metrics,
    }