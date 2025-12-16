from typing import Dict, Optional


def build_prompt(
        transcript:str, 
        bert_analysis:Dict,
        stt_metrics:Optional[Dict]=None,
        weakness_patterns:Optional[Dict]=None,
        evolution_insights:Optional[Dict]=None,
        qa_list:Optional[list[dict]]=None,
        )->str:

    # BERT 결과
    bert_summary="\n".join([
        f"  - {label}: score={data['score']:.2f}, detected={'Yes' if data['label']==1 else 'No'}"
        for label, data in bert_analysis.items()
    ])

    stt_summary=""
    if stt_metrics:
        stt_summary=f"""
[STT 기반 발화 메트릭]
- 전체 발화 시간 : {stt_metrics.get('total_duration_sec', stt_metrics.get('duration_sec', 0))}초
- 평균 말하기 속도 : {stt_metrics.get('avg_speech_rate_wpm', stt_metrics.get('speech_rate_wpm', 0))} WPM
- 총 멈춤 횟수 : {stt_metrics.get('total_pause_count', stt_metrics.get('pause_count', 0))}
- 평균 멈춤 길이 : {stt_metrics.get('avg_pause_duration', 0)}초
- 침묵 비율 : {stt_metrics.get('avg_silence_ratio', stt_metrics.get('silence_ratio', 0))}
- 평균 인식 신뢰도 : {stt_metrics.get('avg_confidence', 0)}
- 낮은 신뢰도 단어 비율 : {stt_metrics.get('avg_low_conf_ratio', 0)}
"""
        
    weakness_summary=""
    if weakness_patterns:
        weakness_summary=f"""
[장기 약점 패턴 분석]
- 반복적으로 나타나는 약점 라벨 : {weakness_patterns.get('weak_labels', [])}
- 문제가 자주 발생한 질문 번호 : {weakness_patterns.get('weak_questions', [])}
- 요약 : {weakness_patterns.get('pattern_summary', '')}
"""
        
    evolution_summary=""
    if evolution_insights:
        improvement=evolution_insights.get("improvement", {})
        evolution_summary=f"""


[말하기 스타일 변화 추세]
- 타임라인 : {evolution_insights.get('timeline', [])}
- 변화 방향 : {improvement.get('direction')}
- 변화율 : {improvement.get('percent')}%
- 시작 점수 → 현재 점수 : {improvement.get('from')} → {improvement.get('to')}
- 요약 : {improvement.get('summary')}
"""

    qa_block=""
    if qa_list:
        qa_lines=[]
        for idx, item in enumerate(qa_list, start=1):
            q=item.get("question", "")
            a=item.get("answer", "")
            qa_lines.append(f"Q{idx}. {q}\nA{idx}. {a}\n")
        qa_block="\n[질문별 Q/A 목록]\n"+"\n".join(qa_lines)



    prompt=f"""
당신은 모의면접 코칭 전문가입니다.
아래 면접 답변을 분석하고, 텍스트 기반으로만 피드백을 제공하세요.


[면접 답변 텍스트]
{transcript}


[질문별 Q/A 목록]
{qa_block}


[BERT 멀티라벨 분석 결과]
{bert_summary}
{stt_summary}
{weakness_summary}
{evolution_summary}


[요구사항]
1. 먼저 이번 면접 답변 자체에 대한 평가를 작성하세요. (논리, 전달력, 표현, 말투 등)
2. 각 질문에 대해, 지원자의 답변이 질문 의도에 얼마나 적합한지 '내용 측면'에서 평가하세요.
3. BERT 결과와 STT 메트릭을 활용하여 구체적인 개선 포인트를 제시하세요.
4. Chroma 기반 장기 패턴(약점, 변화 추세)이 제공된 경우,
    "이 사용자는 평소에 어떤 경향이 있는지"까지 함꼐 설명하세요.
5. 전체 요약, 구체적인 문제점, 개선 방법, 연습 방향을 섹션별로 나누어 JSON 포맷으로 반환하세요.


[분석 가이드]
당신은 위 텍스트와 BERT 결과를 바탕으로, 아래 3가지 항목에 대해 0~100점 척도로 평가하고 구체적인 피드백을 제공해야 합니다.


[세부 규칙]
1. 각 항목의 의미
    - "non-standard":
        - 비표준어, 신조어, 욕설, 과도하게 구어체스러운 표현 등
        - BERT 결과 중 "slang", "curse", "biased"가 1인 경우를 우선 참고하되, 텍스트 내용도 함께 고려하세요.

    - "filler words":
        - "음", "어", "뭐랄까", "약간", "뭔가", "아이씨" 등 발화 사이를 채우는 군더더기 표현
        - BERT 결과의 "filler" 값을 주요 근거로 사용하세요.

    - "discourse_clarity":
        - 문장 구조가 어수선한지, 말이 빙빙 도는지, 앞뒤가 모호한지,
          그리고 면접 상황에 맞는 격식을 유지하고 있는지 등을 평가합니다.
        - BERT 결과 중 "formality inconsistency", "disfluncy/repetition", "vague", "ending_da"를 참고하세요.
    
    
    - non_standard 점수를 정할 때는, BERT 라벨 중 "slang", "biased", "curse"의 label과 score를 우선적으로 반영하세요.
    - filler_words 점수를 정할 때는 BERT 라벨 "filler"만을 가장 중요하게 반영하세요.
    - discourse_clarity 점수를 정할 때는 "formality inconsistency", "disfluency/repetition", "vague", "ending_da" 네 가지를 종합적으로 고려하세요.

2. score(0~100점 정수)
    - 0~20 : 문제 없음
    - 21~40 : 아주 약한 정도로 존재
    - 41~60 : 약하게 존재
    - 61~80 : 자주 나타나서 전달력에 영향
    - 81~100 : 심각하여 발화 이해에 큰 방해

3. BERT 결과 반영 방식
    - BERT에서 label=1이고 score 높을수록, 해당 항목의 score를 높게 책정하세요.
    - BERT에서 label=0인 항목은 score를 60 이상으로 주지 마세요.
    - 텍스트를 직접 읽고 보정할 수 있지만, BERT의 신호를 기본값으로 존중해야 합니다.

4. 예시/근거
    - "detected_examples"에는 실제 문장 말투 일부 또는 표현을 그대로 넣으세요.
    - "reason"에는 왜 그런 판단을 했는지 한 두 문장으로 적으세요.
    - "improvement"에는 사용자가 실제로 어떻게 바꾸면 좋을지, 구체적인 행동 가이드 형식으로 적으세요.
    - "revised_examples"에는 
        - "original": 사용자의 원래 표현
        - "revised" : 더 좋은 표현 예시
        를 1~3개 정도 넣으세요.

5. 제한 사항
    - 감정, 발음, 말 속도, 억양 등 음성 기반 특징은 절대 추론하지 마세요.
    - 제공된 텍스트와 BERT 결과에 없는 정보는 추가로 지어내지 마세요.
    - JSON 이외의 다른 텍스트는 절대 출력하지 마세요.
    - JSON 필드명, 계층 구조, 자료형을 반드시 지키세요,

추가로 'content' 영역에 대해 아래 형식으로 평가하세요.
- content.overall.score : 전체 답변의 내용 적절성(0~100)
- content.overall.strengths : 내용적으로 잘한 점
- content.overall.weaknesses : 내용적으로 부족한 점
- content.overall.summary : 한 문단 요약
- content.per_question[*] : 각 질문별 내용 평가

    
[출력 형식]
- JSON 이외의 다른 텍스트는 절대 출력하지 마세요.
- JSON 필드명, 계층 구조, 자료형을 반드시 지키세요.

반드시 아래 JSON 형식으로만 응답하세요. 마크다운 코드 블록(```)이나 추가 설명은 절대 포함하지 마세요.

{{
    "non_standard":{{
        "score": <0~100 정수>,
        "detected_examples": ["<예시1>", "<예시2>"],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples":[
            {{"original": "<원문>", "revised": "<수정안>"}},
            {{"original": "<원문>", "revised": "<수정안>"}}
        ]
    }},

    "filler_words":{{
        "score": <0~100 정수>,
        "detected_examples": ["<예시1>", "<예시2>"],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples":[
            {{"original": "<원문>", "revised": "<수정안>"}}
        ]
    }},

    "discourse_clarity":{{
        "score": <0~100 정수>,
        "detected_examples": ["<예시1>", "<예시2>"],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples":[
            {{"original": "<원문>", "revised": "<수정안>"}}
        ]
    }},
    "content_overall":{{
    "score": <0~100 정수>,
    "strengths": ["<내용적으로 잘한 점1>", "<내용적으로 잘한 점2>"],
    "weaknesses": ["<내용적으로 부족한 점1>", "<내용적으로 부족한 점2>"],
    "summary": "<내용 측면 요약>",
    }},

    "content_per_question":[
        {{
        "q_index": 1,
        "q_text": "<질문 텍스트>",
        "score": <0~100 정수>,
        "comment": "<이 답변이 왜 적절/부적절했는지 내용 중심 설명>",
        "suggestion": "<어떻게 말하면 더 좋았을지>",
        }}
    ],

    "overall_comment":"<전체적인 총평을 10문장 이내로 작성>"

}}
""".strip()
    
    return prompt



# 시스템 메시지(OpenAI용)
SYSTEM_MESSAGE="""당신은 취업 면접 전문 코치입니다.

면접자의 답변 텍스트를 분석하고, 말투와 표현의 적절성을 평가하여 구조화된 피드백을 제공합니다.
항상 JSON 형식으로만 응답하며, 텍스트에 기반한 객관적이고 구체적인 조언을 제공합니다."""