from typing import Dict, List


def build_prompt(sentences: List[Dict], stt_data: Dict, bert_analysis: Dict, target_speaker: str):
    """
    Communication 분석용 프롬프트 생성

    Args:
        sentences: 파싱된 문장 리스트 (sentence_index, speaker_label, text, start_time, end_time 포함)
        stt_data: STT 원본 데이터 (단어 단위 타임스탬프 포함)
        bert_analysis: BERT 분석 결과 {'slang': 0/1, 'biased': 0/1, 'curse': 0/1, 'filler': 0/1}
        target_speaker: 분석 대상 화자 (예: "1")
    """

    # BERT 결과 포맷팅
    bert_summary = "\n".join([
        f"  - {label}: detected={'Yes' if value == 1 else 'No'}"
        for label, value in bert_analysis.items()
    ])

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

    prompt = f"""
당신은 커뮤니케이션 능력 평가 전문가입니다.
아래 대화 내용과 타임스탬프 정보를 분석하고, 화자의 발화 특성을 평가하세요.

[대화 데이터]
분석 대상 화자: Speaker {target_speaker}

{sentences_text}

[BERT 분석 결과]
{bert_summary}

[분석 가이드]
다음 항목들을 평가하고 구체적인 피드백을 제공하세요:

1. speed (발화 속도, 단위: 음절/초)
   - 실제로 소리가 나는 조음(말 산출) 시간만을 기준으로 한 속도
   - 타임스탬프 정보를 사용하여 계산
   - 일반적인 적정 범위: 4-5 음절/초

2. speech_rate (말하기 속도, 단위: 음절/초)
   - 휴지(말더듬, 멈춤, 숨고르기 등 비유창성) 포함한 전체 속도
   - 타임스탬프 정보를 사용하여 계산
   - 일반적인 적정 범위: 3-4 음절/초

3. silence (침묵 횟수)
   - 발화 도중 1.5초 이상의 침묵이 발생한 횟수
   - 연속된 문장들의 endTime과 startTime 차이를 계산하여 측정

4. clarity (명료도, 0~100점)
   - 비표준어, 신조어, 욕설, 과도하게 구어체스러운 표현 정도
   - BERT 결과 중 "slang", "curse", "biased"를 주요 근거로 사용
   - 0~20: 문제 없음, 21~40: 약간 존재, 41~60: 보통, 61~80: 자주 나타남, 81~100: 심각

5. meaning_clarity (의미 명료도, 0~100점)
   - 문장 구조의 명확성, 논리적 흐름, 앞뒤 일관성
   - 텍스트 내용을 직접 분석하여 평가
   - 점수 기준은 clarity와 동일

6. cut (필러 워드 사용 횟수)
   - "음", "어", "뭐랄까", "약간", "뭔가" 등 군더더기 표현의 횟수
   - BERT 결과의 "filler"와 텍스트 분석을 함께 사용

7. summary (종합 요약)
   - 전반적인 커뮤니케이션 능력 평가를 5-7문장으로 작성
   - 강점과 개선점을 균형있게 서술

8. advice (개선 조언)
   - 구체적이고 실천 가능한 개선 방법을 5-7문장으로 작성
   - 우선순위가 높은 항목부터 제시

[중요 지침 - detected_examples 및 revised_examples]
1. detected_examples에는 문제가 발견된 Sentence 인덱스 번호만 배열로 반환하세요.
   - 예: "detected_examples": [0, 2, 5]
   - Sentence 인덱스는 0부터 시작합니다.
   - 문제가 발견되지 않으면 빈 배열 []을 반환하세요.

2. revised_examples의 original에도 Sentence 인덱스 번호만 입력하세요.
   - 예: {{"original": 2, "revised": "개선된 표현"}}
   - revised에는 개선된 표현 예시를 텍스트로 작성하세요.

3. reason에는 해당 항목에 대한 판단 근거를 한두 문장으로 작성하세요.

4. improvement에는 구체적이고 실천 가능한 개선 방법을 작성하세요.

[제한 사항]
- 제공된 타임스탬프와 텍스트, BERT 결과에 기반하여 분석하세요
- 추측이나 근거 없는 정보를 추가하지 마세요
- JSON 이외의 다른 텍스트는 절대 출력하지 마세요

[출력 형식]
반드시 아래 JSON 형식으로만 응답하세요. 마크다운 코드 블록(```)이나 추가 설명은 절대 포함하지 마세요.

{{
    "speed": {{
        "score": <float, 음절/초>,
        "detected_examples": [0, 2],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples": [
            {{"original": 0, "revised": "개선된 표현 예시"}},
            {{"original": 2, "revised": "개선된 표현 예시"}}
        ]
    }},
    "speech_rate": {{
        "score": <float, 음절/초>,
        "detected_examples": [],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples": []
    }},
    "silence": {{
        "score": <int, 침묵 횟수>,
        "detected_examples": [],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples": []
    }},
    "clarity": {{
        "score": <int, 0~100>,
        "detected_examples": [1, 3],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples": [
            {{"original": 1, "revised": "개선된 표현"}},
            {{"original": 3, "revised": "개선된 표현"}}
        ]
    }},
    "meaning_clarity": {{
        "score": <int, 0~100>,
        "detected_examples": [],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples": []
    }},
    "cut": {{
        "score": <int, 필러 워드 횟수>,
        "detected_examples": [0, 2, 4],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>",
        "revised_examples": [
            {{"original": 0, "revised": "개선된 표현"}}
        ]
    }},
    "summary": "<종합 요약 5-7문장>",
    "advice": "<개선 조언 5-7문장>"
}}
""".strip()

    return prompt


SYSTEM_MESSAGE = """당신은 커뮤니케이션 능력 평가 전문가입니다.
화자의 발화를 분석하여 발화 속도, 명료도, 침묵 패턴 등을 평가하고 구조화된 피드백을 제공합니다.
타임스탬프 정보를 활용하여 정량적 지표를 계산하고, 텍스트 분석을 통해 정성적 평가를 수행합니다.
항상 JSON 형식으로만 응답하며, 객관적이고 구체적인 조언을 제공합니다.
detected_examples와 revised_examples의 original에는 반드시 Sentence 인덱스 번호(정수)만 반환해야 합니다."""
