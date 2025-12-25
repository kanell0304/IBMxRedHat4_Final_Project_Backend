from typing import Dict, Any, List
from app.service.llm_service import OpenAIService
import json


# 영어 면접 종합 분석
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


    prompt=f"""당신은 영어 면접 코치입니다. 다음 영어 면접 성과를 분석해주세요.

[면접 전체 스크립트]
{transcript}

[질문/답변]
{format_qa_list(qa_list)}

[발화 메트릭]
- 말하기 속도(WPM):{speech_rate:.2f}
- 침묵 비율(pause ratio):{pause_ratio:.1%}
- 확실한 추임새(hard filler:uh/um/er/ah 등):{filler_hard}회
- 조건부 추임새(soft filler:like/so/well 등):{filler_soft}회

[평가 기준(참고)]
1) 말하기 속도(WPM)
- 120 미만:느려서 답변이 약해 보일 수 있음(다만 신중한 답변이면 예외 가능)
- 120~170:일반적으로 안정적
- 170 초과:빠르게 들릴 수 있어 발음/명료성이 떨어지면 감점

2) 침묵 비율(pause ratio)
- 0~15%:매우 안정적
- 15~30%:보통
- 30% 초과:끊김이 잦아 유창성 저하 가능

3) 추임새
- hard filler는 대부분 불필요한 머뭇거림으로 간주
- soft filler는 문맥상 정상일 수 있으나 과도하면 감점 가능

[요구사항]
아래 3가지를 제공해라:
1) 종합 점수(0~100 정수)
2) 코멘트 3줄(각 1문장, 한국어):
   - 내용(구성/논리/구체성)
   - 전달/유창성(속도/침묵/추임새 포함) — 수치를 근거로 언급할 것
   - 개선 포인트(가장 임팩트 큰 1~2개) — 구체적 행동 제안 포함

반드시 JSON만 출력해라. 다른 텍스트/설명은 금지.
출력 형식:
{{
  "score":<number>,
  "comments":[
    "<comment 1>",
    "<comment 2>",
    "<comment 3>"
  ]
}}
"""

    response=await llm_service.client.chat.completions.create(
        model=llm_service.model,
        messages=[
            {"role": "system", "content": "너는 영어 면접 평가자다. 반드시 유효한 JSON만 출력해라."},
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

    return {
        "score":result.get("score", 70),
        "comments":result.get(
            "comments",
            [
                "내용은 전반적으로 무난하지만 핵심 메시지와 근거 예시가 더 필요합니다.",
                f"말하기 속도 {speech_rate:.0f} WPM, 침묵 비율 {pause_ratio:.0%}, hard filler {filler_hard}회로 유창성은 보통 수준입니다.",
                "답변을 2~3개의 포인트로 먼저 구조화한 뒤, 각 포인트마다 1개의 구체 예시를 붙이는 연습을 하세요.",
            ],
        ),
        "stt_metrics":stt_metrics,
        "transcript":transcript,
    }


def format_qa_list(qa_list:List[Dict[str, Any]])->str:
    formatted=[]
    for i, qa in enumerate(qa_list, 1):
        formatted.append(f"Q{i}:{qa.get('question', '')}")
        formatted.append(f"A{i}:{qa.get('answer', '')}")
        formatted.append("")
    return "\n".join(formatted)