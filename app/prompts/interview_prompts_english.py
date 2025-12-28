from typing import Dict


def build_english_interview_prompt(
        transcript:str,
        stt_metrics:Dict,
        qa_list:list
)->str:
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

    qa_lines=[]
    for i, qa in enumerate(qa_list, 1):
        qa_lines.append(f"Q{i}:{qa.get('question', '')}")
        qa_lines.append(f"A{i}:{qa.get('answer', '')}")
        qa_lines.append("")
    qa_block="\n".join(qa_lines)

    prompt=f"""당신은 영어 면접 코치입니다. 다음 영어 면접 성과를 분석해주세요.

[면접 전체 스크립트]
{transcript}

[질문/답변]
{qa_block}

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
아래 4가지를 제공해라:
1) 종합 점수(0~100 정수)
2) 코멘트 3줄(각 1문장, 한국어):
   - 내용(구성/논리/구체성)
   - 전달/유창성(속도/침묵/추임새 포함) — 수치를 근거로 언급할 것
   - 전반적 총평
3) 개선사항 2~3개(각 1문장, 한국어):
   - 가장 임팩트 큰 개선 포인트
   - 구체적이고 실행 가능한 행동 제안

반드시 JSON만 출력해라. 다른 텍스트/설명은 금지.
출력 형식:
{{
  "score":<number>,
  "comments":[
    "<comment 1>",
    "<comment 2>",
    "<comment 3>"
  ],
  "improvements":[
    "<improvement 1>",
    "<improvement 2>"
  ]
}}
"""
    return prompt.strip()


ENGLISH_SYSTEM_MESSAGE="너는 영어 면접 평가자다. 반드시 유효한 JSON만 출력해라."
