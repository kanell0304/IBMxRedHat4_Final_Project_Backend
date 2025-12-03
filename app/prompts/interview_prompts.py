from typing import Dict



def build_prompt(transcript:str, bert_analysis:Dict):

    # BERT 결과
    bert_summary="\n".join([
        f"  - {label}: score={data['score']:.2f}, detected={'Yes' if data['label']==1 else 'No'}"
        for label, data in bert_analysis.items()
    ])


    prompt=f"""
당신은 모의면접 코칭 전문가입니다.
아래 면접 답변을 분석하고, 텍스트 기반으로만 피드백을 제공하세요.


[면접 답변 텍스트]
{transcript}



[BERT 멀티라벨 분석 결과]
{bert_summary}



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
        - 문장 구조가 어수선한지, 말이 빙빙 도는지, 앞뒤가 모호한지 등
        - BERT 결과 중 "formality inconsistency", "disfluncy/repetition", "vague"를 참고하세요.
    
    
    - non_standard 점수를 정할 때는, BERT 라벨 중 "slang", "biased", "curse"의 label과 score를 우선적으로 반영하세요.
    - filler_words 점수를 정할 때는 BERT 라벨 "filler"만을 가장 중요하게 반영하세요.
    - discourse_clarity 점수를 정할 때는 "formality inconsistency", "disfluency/repetition", "vague" 3가지를 종합적으로 고려하세요.

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
    "overall_comment": "<전반적인 총평을 10문장 이내로 작성>"

}}
""".strip()
    
    return prompt



# 시스템 메시지(OpenAI용)
SYSTEM_MESSAGE="""당신은 취업 면접 전문 코치입니다.
면접자의 답변 텍스트를 분석하고, 말투와 표현의 적절성을 평가하여 구조화된 피드백을 제공합니다.
항상 JSON 형식으로만 응답하며, 텍스트에 기반한 객관적이고 구체적인 조언을 제공합니다."""