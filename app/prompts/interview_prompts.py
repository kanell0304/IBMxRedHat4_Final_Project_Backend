from typing import Dict, Optional


def build_prompt(
        transcript:str, 
        bert_analysis:Dict,
        stt_metrics:Optional[Dict]=None,
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
        
    qa_block=""
    if qa_list:
        qa_lines=[]
        for idx, item in enumerate(qa_list, start=1):
            q=item.get("question", "")
            a=item.get("answer", "")
            qa_lines.append(f"Q{idx}. {q}\nA{idx}. {a}\n")
        qa_block="\n".join(qa_lines)



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


[요구사항]
1. 먼저 이번 면접 답변 자체에 대한 평가를 작성하세요. (논리, 전달력, 표현, 말투 등)
2. 각 질문에 대해, 지원자의 답변이 질문 의도에 얼마나 적합한지 '내용 측면'에서 평가하세요.
3. BERT 결과와 STT 메트릭을 활용하여 구체적인 개선 포인트를 제시하세요.
4. 전체 요약, 구체적인 문제점, 개선 방법, 연습 방향을 섹션별로 나누어 JSON 포맷으로 반환하세요.


[분석 가이드]
당신은 위 텍스트와 BERT 결과를 바탕으로, 아래 3가지 항목에 대해 0~100점 척도로 평가하고 구체적인 피드백을 제공해야 합니다.
모든 score는 0~100 정수로만 제공하세요. 등급(grade)은 자동으로 변환됩니다.
- 90~100점 : S등급
- 80~89점 : A등급
- 70~79점 : B등급
- 60~69점 : C등급
- 0~59점 : D등급

[세부 규칙]
1. 각 항목의 의미
    - "언어 정확성" (language_accuracy):
        - 비표준어, 신조어, 욕설, 과도하게 구어체스러운 표현 등
        - BERT 결과 중 "slang", "curse", "biased"가 1인 경우를 우선 참고하되, 텍스트 내용도 함께 고려하세요.

    - "발화 간결성" (speech_conciseness):
        - "음", "어", "뭐랄까", "약간", "뭔가", "아이씨" 등 발화 사이를 채우는 군더더기 표현
        - BERT 결과의 "filler" 값을 주요 근거로 사용하세요.

    - "구조 명확성" (structural_clarity):
        - 문장 구조가 어수선한지, 말이 빙빙 도는지, 앞뒤가 모호한지,
          그리고 면접 상황에 맞는 격식을 유지하고 있는지 등을 평가합니다.
        - BERT 결과 중 "formality_inconsistency", "disfluency_repetition", "vague", "ending_da"를 참고하세요.


    - 언어 정확성 점수 결정 시, BERT 라벨 중 "slang", "biased", "curse"의 label과 score를 우선적으로 반영하되,
      실제 텍스트가 '차별/비하/욕설'에 해당하는지 한 번 더 확인하세요. 단순한 짧은 대답(예: "네.", "맞습니다.")은 편향/욕설로 판단하지 않습니다.
    - 발화 간결성 점수를 정할 때는 BERT 라벨 중 "filler"만을 가장 중요하게 반영하세요.
    - 구조 명확성 점수를 결정할 때 "formality_inconsistency", "disfluency_repetition", "vague", "ending_da" 네 가지를 종합적으로 고려하세요.

2. score(0~100점 정수) - 품질 점수(높을수록 좋음)
    - 90~100 : 문제 없음 (S등급)
    - 80~89 : 아주 약한 정도로 존재 (A등급)
    - 70~79 : 약하게 존재 (B등급)
    - 60~69 : 자주 나타나서 전달력에 영향 (C등급)
    - 0~59 : 심각하여 발화 이해에 큰 방해 (D등급)

3. BERT 결과 반영 방식
    - BERT에서 label=1이고 score 높을수록, 해당 항목의 품질 score는 낮게 책정하세요.
    - BERT에서 label=0인 항목은 품질 score를 80 이상으로 주세요.
    - 텍스트를 직접 읽고 보정할 수 있지만, BERT의 신호를 기본값으로 존중해야 합니다.
    - 터무니 없이 BERT 라벨 결과가 틀렸을 경우, score를 조정해주세요.
        - 예시 : 욕설이 아예 없는 문장임에도 curse=1일 경우

4. 예시/근거 (score에 따라 다르게 작성)
    - "detected_examples"에는:
        - score 80 미만: 실제 문제가 되는 문장 말투나 표현을 넣으세요.
        - score 80 이상: 빈 리스트 []로 남겨두거나, 좋은 표현 예시를 넣으세요.
    - "reason"에는:
        - score 80 미만: 왜 그런 판단을 했는지 한 두 문장으로 적으세요.
        - score 80 이상: "전반적으로 문제없이 잘 구사하고 있습니다" 등 긍정적 평가를 적으세요.
    - "improvement"에는:
        - score 80 미만: 사용자가 실제로 어떻게 바꾸면 좋을지, 구체적인 행동 가이드 형식으로 적으세요.
        - score 80 이상: "현재 수준을 유지하면 좋습니다" 또는 "계속 격식 있는 표현을 사용하세요" 등 유지/강화 메시지를 적으세요.
    - "revised_examples"에는:
        - score 80 미만:
            - "original": 사용자의 원래 표현
            - "revised" : 더 좋은 표현 예시
            를 1~3개 정도 넣으세요.
        - score 80 이상: 빈 리스트 []로 남겨두거나, 현재 좋은 표현을 "original"과 "revised"에 동일하게 넣으세요.

5. 제한 사항
    - 감정, 발음, 말 속도, 억양 등 음성 기반 특징은 절대 추론하지 마세요.
    - 제공된 텍스트와 BERT 결과에 없는 정보는 추가로 지어내지 마세요.
    - JSON 이외의 다른 텍스트는 절대 출력하지 마세요.
    - JSON 필드명, 계층 구조, 자료형을 반드시 지키세요.

추가로 'content' 영역에 대해 아래 형식으로 평가하세요.
- content.overall.score : 전체 답변의 내용 적절성(0~100)
- content.overall.strengths : 내용적으로 잘한 점
- content.overall.weaknesses : 내용적으로 부족한 점
- content.overall.summary : 한 문단 요약
- content.per_question : 위 [질문별 Q/A 목록]에 제시된 모든 질문에 대해 각각 평가

[질문별 평가 세부 지침]
**매우 중요:
1. [질문별 Q/A 목록]에 나열된 모든 질문(Q1, Q2, Q3, ...)에 대해 빠짐없이 평가하세요.
2. 각 질문별 평가는 반드시 서로 달라야 합니다.**

1. 질문 의도 파악 (question_intent):
   - 각 질문이 무엇을 묻고 있는지 명확히 분석하세요.
   - "지원 동기", "강점/약점", "문제 해결 능력", "협업 경험", "미래 계획" 등 질문 유형을 구분하세요.
   - 질문마다 다른 의도를 가지므로, 절대 같은 표현을 반복하지 마세요.

2. 답변-질문 적합성 판단 (is_appropriate):
   - 먼저 question_intent에서 파악한 질문의 핵심 의도를 기준으로 삼으세요.
   - 답변이 그 의도에 직접적으로 대답하는지 평가하세요.

   **true로 판단하는 경우 (초록 배지 "적절"):**
   - 질문의 핵심 의도에 직접 답변함
   - 예: "지원 동기" 질문에 회사/직무에 대한 관심과 본인의 fit을 설명

   **false로 판단하는 경우 (빨간 배지 "개선필요"):**
   - 질문과 완전히 무관한 내용으로 답변
   - 질문을 회피하거나 다른 주제로 전환
   - 부분적으로만 답하고 핵심을 놓침
   - 예: "지원 동기" 질문에 자기 경력만 나열하고 회사/직무와의 연결성 없음

   **중요:** question_intent에서 파악한 의도와 실제 답변 내용을 비교하여 판단하세요.

3. 구체적인 평가 (comment):
   - "좋았다/부족했다"와 같은 일반적 표현 금지.
   - 해당 질문의 의도와 연관지어 구체적으로 서술하세요.
   - 예: "지원 동기를 묻는 질문에 회사에 대한 관심보다 개인적 성장에만 집중하여 답변의 초점이 어긋났습니다."

4. 차별화된 개선 제안 (suggestion):
   - 각 질문의 특성에 맞는 구체적인 개선 방향을 제시하세요.
   - 다른 질문과 중복되지 않는 실행 가능한 조언을 제공하세요.
   - 예: "지원 동기 질문에는 '회사의 OO 가치와 본인의 OO 경험을 연결'하는 식으로 답변하세요."

5. 근거 문장 (evidence_sentences):
   - 반드시 해당 질문(q_index)에 대한 답변에서만 추출하세요.
   - 다른 질문의 답변을 섞지 마세요.
   - 평가 근거가 되는 핵심 문장 1~3개를 선택하세요.

**금지 사항:**
- 모든 질문에 대해 "전반적으로 좋았으나 구체성이 부족합니다" 같은 동일한 패턴 반복 금지
- comment와 suggestion이 5개 질문에서 비슷한 내용으로 나오는 것 금지
- question_intent가 "질문의 의도를 파악하기 위한 질문입니다" 같은 무의미한 문장 금지


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
        "q_text": "<질문1 텍스트>",
        "score": <0~100 정수>,
        "comment": "<이 답변이 왜 적절/부적절했는지 내용 중심 설명>",
        "suggestion": "<어떻게 말하면 더 좋았을지>",
        "question_intent": "<질문의 의도를 한 문장으로 요약>",
        "is_appropriate": <true 또는 false, 답변이 질문 의도에 맞는지>,
        "evidence_sentences": ["<근거가 되는 사용자 답변 문장1>", "<근거가 되는 사용자 답변 문장2>"]
        }},
        {{
        "q_index": 2,
        "q_text": "<질문2 텍스트>",
        "score": <0~100 정수>,
        "comment": "<이 답변이 왜 적절/부적절했는지 내용 중심 설명>",
        "suggestion": "<어떻게 말하면 더 좋았을지>",
        "question_intent": "<질문의 의도를 한 문장으로 요약>",
        "is_appropriate": <true 또는 false, 답변이 질문 의도에 맞는지>,
        "evidence_sentences": ["<근거가 되는 사용자 답변 문장1>", "<근거가 되는 사용자 답변 문장2>"]
        }},
        ... (위 [질문별 Q/A 목록]의 모든 질문에 대해 동일한 형식으로 평가)
    ],

    "overall_comment":"<전체적인 총평을 15~20문장으로 상세하게 작성. 언어 정확성, 발화 간결성, 구조 명확성 각각에 대한 평가와 함께 내용 적절성, 질문별 답변 차별성, 전반적인 인상, 강점, 약점, 개선 방향을 종합적으로 서술하세요.>"

}}
""".strip()
    
    return prompt



# 시스템 메시지(OpenAI용)
SYSTEM_MESSAGE="""당신은 취업 면접 전문 코치입니다.

면접자의 답변 텍스트를 분석하고, 말투와 표현의 적절성을 평가하여 구조화된 피드백을 제공합니다.
항상 JSON 형식으로만 응답하며, 텍스트에 기반한 객관적이고 구체적인 조언을 제공합니다."""
