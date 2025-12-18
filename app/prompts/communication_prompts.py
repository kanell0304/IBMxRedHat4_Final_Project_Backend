from typing import Dict, List


def build_prompt(sentences: List[Dict], stt_data: Dict, target_speaker: str, bert_result: Dict = None):
    """
    Communication 분석용 프롬프트 생성

    Args:
        sentences: 파싱된 문장 리스트 (sentence_index, speaker_label, text, start_time, end_time 포함)
        stt_data: STT 원본 데이터 (단어 단위 타임스탬프 포함)
        target_speaker: 분석 대상 화자 (예: "1")
        bert_result: BERT 분석 결과 (curse_count, filler_count 포함)
    """

    # target_speaker의 문장만 필터링
    target_sentences = [s for s in sentences if s["speaker_label"] == target_speaker]

    # 문장 포맷팅 (sentence_index 명확하게 표시)
    formatted_sentences = []
    for sent in target_sentences:
        formatted_sentences.append(
            f"### Sentence [{sent['sentence_index']}] ###\n"
            f"Speaker: {sent['speaker_label']}\n"
            f"Time: {sent['start_time']} - {sent['end_time']}\n"
            f"Text: {sent['text']}\n"
        )

    sentences_text = "\n".join(formatted_sentences)

    # BERT 결과 포맷팅
    bert_info = ""
    if bert_result:
        curse_count = bert_result.get("curse", 0)
        filler_count = bert_result.get("filler", 0)
        bert_info = f"""
[BERT 분석 결과]
- 욕설 감지 횟수: {curse_count}회
- 필러 감지 횟수: {filler_count}회
(중요: sentence_feedbacks에서 curse와 filler 카테고리의 총 개수는 위 횟수와 정확히 일치해야 합니다)
"""

    prompt = f"""
당신은 커뮤니케이션 능력 평가 전문가입니다.
아래 대화 내용과 타임스탬프 정보를 분석하고, 화자의 발화 특성을 평가하세요.

[대화 데이터]
분석 대상 화자: Speaker {target_speaker}

{sentences_text}
{bert_info}

[분석 가이드]
다음 항목들을 평가하고 구체적인 피드백을 제공하세요:

1. speaking_speed (발화 속도, 단위: 음절/초)
   - 순수 조음 속도와 휴지 포함 속도를 모두 계산하여 종합 평가
   - 계산 방법:
     * 순수 조음 속도: 실제 소리가 나는 말 산출 시간 대비 음절 수 (적정: 4-5 음절/초)
     * 휴지 포함 속도: 휴지(멈춤, 숨고르기 등) 포함 전체 시간 대비 음절 수 (적정: 3-4 음절/초)
   - 최종 점수: 두 값의 평균 (단, 두 값이 80% 이상 차이나면 더 높은 값만 사용)
   - 일반적인 적정 범위: 3.5-4.5 음절/초

2. silence (침묵 횟수)
   - 발화 도중 1.5초 이상의 침묵이 발생한 횟수
   - 연속된 문장들의 endTime과 startTime 차이를 계산하여 측정

3. clarity (발음, 0~100점)
   - STT 결과에서 신뢰도가 낮은 단어와 맥락상 어색한 단어를 각각 식별
   - 두 목록에서 중복되는 단어들이 전체 발화에서 차지하는 비율로 발음 정확성 평가
   - 중복 단어 비율이 높을수록 발음 오류가 많다고 판단
   - 0~20: 발음 우수, 21~40: 약간의 발음 오류, 41~60: 보통, 61~80: 발음 오류 빈번, 81~100: 발음 오류 심각

4. meaning_clarity (의미 명료도, 0~100점)
   - 문장 구조의 명확성, 논리적 흐름, 앞뒤 일관성
   - 텍스트 내용을 직접 분석하여 평가
   - 점수 기준은 clarity와 동일

5. cut (말 끊기 횟수)
   - 화자가 말을 끝내기 전에 상대방이 끼어든 횟수
   - 판단 기준 (모두 충족 시 말 끊기로 간주):
     1) 화자가 변경됨
     2) 화자 변경 전후 간격이 0.5초 이하로 짧음 (타임스탬프 분석)
     3) 변경 전 문장이 완성되지 않음 (문맥상 문장이 끝나지 않은 상태)
   - 문장 완성도는 종결어미 유무, 문맥의 완결성을 종합적으로 판단

6. curse (욕설)
   - BERT가 감지한 욕설 개수와 정확히 일치하도록 문장 선택
   - 욕설이나 비속어가 포함된 문장 식별

7. filler (필러)
   - BERT가 감지한 필러 개수와 정확히 일치하도록 문장 선택
   - "음", "어", "그", "뭐" 등 의미 없는 말버릇 식별

8. summary (종합 요약)
   - 전반적인 커뮤니케이션 능력 평가를 5-7문장으로 작성
   - 강점과 개선점을 균형있게 서술

9. advice (개선 조언)
   - 구체적이고 실천 가능한 개선 방법을 5-7문장으로 작성
   - 우선순위가 높은 항목부터 제시

[중요 지침]
1. detected_examples에는 문제가 발견된 Sentence 인덱스 번호만 배열로 반환하세요.
   - 예: "detected_examples": [0, 2, 5]
   - Sentence 인덱스는 0부터 시작합니다.
   - 문제가 발견되지 않으면 빈 배열 []을 반환하세요.

2. reason에는 해당 항목에 대한 판단 근거를 한두 문장으로 작성하세요.

3. improvement에는 구체적이고 실천 가능한 개선 방법을 작성하세요.

4. sentence_feedbacks에는 각 문장별 구체적인 피드백을 작성하세요.
   - 분석 대상 화자의 문장에만 피드백 추가
   - 각 피드백은 간결한 한 줄 요약 형식 (예: "너무 빠름", "'음' 사용")
   - curse와 filler의 총 개수는 BERT 결과와 정확히 일치해야 함
   - 문제가 없는 문장은 sentence_feedbacks에 포함하지 않음

[제한 사항]
- 제공된 타임스탬프와 텍스트에 기반하여 분석하세요
- 추측이나 근거 없는 정보를 추가하지 마세요
- JSON 이외의 다른 텍스트는 절대 출력하지 마세요

[출력 형식]
반드시 아래 JSON 형식으로만 응답하세요. 마크다운 코드 블록(```)이나 추가 설명은 절대 포함하지 마세요.

{{
    "speaking_speed": {{
        "score": <float, 음절/초>,
        "detected_examples": [0, 2],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "silence": {{
        "score": <int, 침묵 횟수>,
        "detected_examples": [],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "clarity": {{
        "score": <int, 0~100>,
        "detected_examples": [1, 3],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "meaning_clarity": {{
        "score": <int, 0~100>,
        "detected_examples": [],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "cut": {{
        "score": <int, 말 끊기 횟수>,
        "detected_examples": [0, 2, 4],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "curse": {{
        "detected_examples": [1],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "filler": {{
        "detected_examples": [0, 3],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "summary": "<종합 요약 5-7문장>",
    "advice": "<개선 조언 5-7문장>",
    "sentence_feedbacks": [
        {{
            "sentence_index": 0,
            "feedbacks": [
                {{"category": "speaking_speed", "message": "너무 빠름"}},
                {{"category": "filler", "message": "'음' 사용"}}
            ]
        }},
        {{
            "sentence_index": 2,
            "feedbacks": [
                {{"category": "speaking_speed", "message": "말이 빠르고 명확하지 않음"}}
            ]
        }}
    ]
}}
""".strip()

    return prompt


SYSTEM_MESSAGE = """당신은 커뮤니케이션 능력 평가 전문가입니다.
화자의 발화를 분석하여 발화 속도, 발음, 의미 명료도, 침묵 패턴, 말 끊기, 욕설, 필러 등을 평가하고 구조화된 피드백을 제공합니다.
타임스탬프 정보를 활용하여 정량적 지표를 계산하고, 텍스트 분석을 통해 정성적 평가를 수행합니다.
항상 JSON 형식으로만 응답하며, 객관적이고 구체적인 조언을 제공합니다.
detected_examples에는 반드시 Sentence 인덱스 번호(정수)만 반환해야 하고, sentence_feedbacks에는 각 문장별 간결한 피드백 메시지를 제공해야 합니다."""
