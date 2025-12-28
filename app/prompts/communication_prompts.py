from typing import Dict, List


def parse_time(time_str: str) -> float:
    """시간 문자열(예: '1.234s')을 float로 변환"""
    return float(time_str.replace('s', ''))


def extract_filler_durations(stt_data: Dict, sentence: Dict) -> List[Dict]:
    """
    문장에 포함된 filler 단어들의 duration 추출

    Returns:
        [{"word": "음", "duration": 0.8}, ...]
    """
    FILLER_WORDS = ["음", "어", "어 음"]
    filler_info = []

    sent_start = parse_time(sentence['start_time'])
    sent_end = parse_time(sentence['end_time'])

    if "results" not in stt_data:
        return filler_info

    for result in stt_data["results"]:
        if "alternatives" not in result or not result["alternatives"]:
            continue

        alt = result["alternatives"][0]
        if "words" not in alt:
            continue

        for word_info in alt["words"]:
            word = word_info.get("word", "")
            word_start = parse_time(word_info.get("startTime", "0s"))
            word_end = parse_time(word_info.get("endTime", "0s"))
            speaker = word_info.get("speakerLabel", "1")

            # 해당 문장 범위 내의 단어만
            if speaker == sentence['speaker_label'] and sent_start <= word_start < sent_end:
                # filler 단어인지 확인
                if word in FILLER_WORDS:
                    duration = word_end - word_start
                    filler_info.append({"word": word, "duration": round(duration, 2)})

    return filler_info


def build_prompt(sentences: List[Dict], stt_data: Dict, target_speaker: str, bert_result: Dict = None, bert_sentence_results: Dict = None):
    """
    Communication 분석용 프롬프트 생성

    Args:
        sentences: 파싱된 문장 리스트 (sentence_index, speaker_label, text, start_time, end_time 포함)
        stt_data: STT 원본 데이터 (단어 단위 타임스탬프 포함)
        target_speaker: 분석 대상 화자 (예: "1")
        bert_result: BERT 분석 결과 (curse_count, filler_count 포함)
        bert_sentence_results: 문장별 BERT 분석 결과 (sentence_index -> issue list)
    """

    # 전체 문장 포맷팅 (말 끊기 판단을 위해 전체 대화 맥락 제공)
    formatted_sentences = []
    for sent in sentences:
        is_target = sent['speaker_label'] == target_speaker
        text_content = sent['text']

        # Filler duration annotation 추가 (모든 화자)
        filler_durations = extract_filler_durations(stt_data, sent)
        if filler_durations:
            duration_annotations = []
            for f in filler_durations:
                annotation = f"'{f['word']}' ({f['duration']}초)"
                if f['duration'] >= 0.5:
                    annotation += " [추임새?]"
                duration_annotations.append(annotation)
            text_content += f" | Filler 후보: {', '.join(duration_annotations)}"

        # BERT 감지 결과 추가 (target_speaker만)
        if is_target and bert_sentence_results and sent['sentence_index'] in bert_sentence_results:
            issues = bert_sentence_results[sent['sentence_index']]
            if issues:
                text_content += f" | BERT 감지: {', '.join(issues)}"

        # 분석 대상 화자 표시
        speaker_marker = " [분석 대상]" if is_target else ""

        formatted_sentences.append(
            f"### Sentence [{sent['sentence_index']}] ###\n"
            f"Speaker: {sent['speaker_label']}{speaker_marker}\n"
            f"Time: {sent['start_time']} - {sent['end_time']}\n"
            f"Text: {text_content}\n"
        )

    sentences_text = "\n".join(formatted_sentences)

    # BERT 결과 포맷팅
    bert_info = ""
    if bert_result:
        curse_count = bert_result.get("curse", 0)
        filler_count = bert_result.get("filler", 0)
        biased_count = bert_result.get("biased", 0)
        slang_count = bert_result.get("slang", 0)
        
        bert_info = f"""
[BERT 분석 결과]
- 욕설 감지 횟수: {curse_count}회
- 차별/비하 발언 감지 횟수: {biased_count}회
- 필러 감지 횟수: {filler_count}회 (참고용, duration 정보 우선)
- 비표준어(Slang) 감지 횟수: {slang_count}회
(중요: curse, biased, slang은 BERT 횟수와 정확히 일치해야 함. filler는 duration 기반으로 독립 판단)
"""

    prompt = f"""
당신은 커뮤니케이션 능력 평가 전문가입니다.
아래 대화 내용과 타임스탬프 정보를 분석하고, 화자의 발화 특성을 평가하세요.

[대화 데이터]
분석 대상 화자: Speaker {target_speaker} ([분석 대상] 표시)
전체 대화를 제공합니다. 분석은 [분석 대상] 화자에 대해서만 수행하세요.
단, 말 끊기 판단을 위해 상대방 화자의 발화 정보도 함께 제공합니다.

{sentences_text}
{bert_info}

[분석 가이드]
다음 항목들을 평가하고 구체적인 피드백을 제공하세요.
**중요: 분석 대상은 Speaker {target_speaker} ([분석 대상] 표시)만이며, detected_examples와 sentence_feedbacks는 분석 대상 화자의 문장에만 추가해야 합니다.**

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
   - **[분석 대상] 화자가 상대방의 말을 끊고 끼어든 횟수**
   - 판단 기준 (모두 충족 시 말 끊기로 간주):
     1) [분석 대상] 화자가 발화를 시작함
     2) 직전 문장이 상대방(다른 Speaker) 발화임
     3) 직전 상대방 문장의 end_time과 현재 문장의 start_time 간격이 0.5초 이하
     4) **직전 상대방 문장이 불완전하게 끝남** (종결어미 없음, 문맥상 미완성, "...", "근데", "그래서" 등)
   - detected_examples에는 [분석 대상] 화자가 끼어든 문장의 sentence_index를 기록
   - 예: 상대 "그게 말이야..." (불완전) → [분석 대상] "아니 그게 아니라" (끼어듦) → detected_examples에 후자 인덱스 추가

6. curse (욕설)
   - BERT가 감지한 욕설 개수와 정확히 일치하도록 문장 선택
   - 욕설이나 비속어가 포함된 문장 식별

7. biased (차별/비하)
   - BERT가 감지한 차별/비하 발언 개수와 정확히 일치하도록 문장 선택
   - 장애인 비하, 혐오 표현, 차별적 언어가 포함된 문장 식별

8. filler (필러)
   - **Filler 후보** annotation을 참고하여 판단
   - 0.5초 이상 길게 끈 경우 ([추임새?] 표시) 추임새로 판정
   - 0.5초 미만이라도 문맥상 의미 없는 습관어라면 추임새로 판정
   - "음", "어" 등이 감탄사나 긍정의 의미로 사용된 경우는 제외
   - BERT 감지 결과도 함께 참고하되, duration 정보를 우선적으로 고려

9. slang (비표준어)
   - BERT가 감지한 비표준어 개수와 정확히 일치하도록 문장 선택
   - 줄임말, 신조어, 인터넷 용어, 방언 등 식별

10. summary (종합 요약)
   - 전반적인 커뮤니케이션 데이터 결과값을 3-4문장으로 작성하십시오.
   - **문장 제약:** '화자', 'Speaker', '당신', '분석 대상', '사람' 등 인칭/대상 지칭어를 절대 사용하지 마십시오.
   - **문장 시작:** 반드시 '발화 속도는', '어휘 선택은', '전체적인 흐름은' 등 분석 항목을 주어로 시작하십시오.
   - 예시: "발화 속도가 적정하여 전달력이 높으나, 문장 끝맺음이 다소 불분명함." (O) / "화자는 발화 속도가 적정합니다." (X)
   - 구성 방식: 각 지표를 단문으로 나열하지 말고, 관련 있는 지표끼리 묶어 인과관계나 대조를 활용해 서술하십시오. (예: 속도는 좋으나 발음이 부정확하여 전달력이 상쇄됨)
   - 접속사 활용: '또한', '반면', '이와 더불어', '따라서' 등의 접속사를 사용하여 문장 간 흐름을 자연스럽게 연결하십시오.
   - 문장 구조: 3-4문장 내외로 작성하되, 핵심 지표들이 서로 어떻게 영향을 주는지 통합적인 관점에서 서술하십시오.

11. advice (개선 조언)
   - 실천 가능한 개선 지침을 3-4문장으로 작성하십시오.
   - **문장 제약:** 명령형(~하십시오) 대신 '필요함', '권장됨', '도움이 됨' 등의 표현을 사용하십시오.
   - **문장 시작:** 개선이 필요한 '항목'이나 '행동'으로 문장을 시작하십시오.
   - 예시: "문장 사이의 휴지를 1초 이상 확보하는 연습이 필요함." (O) / "화자분은 휴지를 확보하세요." (X)

[중요 지침]
1. detected_examples에는 문제가 발견된 Sentence 인덱스 번호만 배열로 반환하세요.
   - **인덱스는 전체 대화에서의 sentence_index를 사용** (### Sentence [N] ###에 표시된 N)
   - **[분석 대상] 표시된 화자의 문장만 선택** (상대방 문장은 절대 포함하지 않음)
   - 예: "detected_examples": [0, 2, 5]
   - 문제가 발견되지 않으면 빈 배열 []을 반환하세요.

2. reason에는 해당 항목에 대한 판단 근거를 한두 문장으로 작성하세요.

3. improvement에는 구체적이고 실천 가능한 개선 방법을 작성하세요.

4. sentence_feedbacks에는 각 문장별 구체적인 피드백을 작성하세요.
   - **[분석 대상] 화자의 문장에만 피드백 추가** (상대방 문장은 제외)
   - 각 피드백은 간결한 한 줄 요약 형식 (예: "너무 빠름", "'음' 사용", "상대 말 끊음")
   - 문제가 없는 문장은 sentence_feedbacks에 포함하지 않음

5. curse, filler, biased, slang의 count 값을 정확히 계산하세요.
   - count: 해당 문제가 포함된 문장의 총 개수
   - detected_examples의 배열 길이와 count 값이 일치해야 함

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
        "count": <int, 욕설이 포함된 문장 개수>,
        "detected_examples": [1],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},


    "filler": {{
        "count": <int, 군말/망설임이 포함된 문장 개수>,
        "detected_examples": [0, 3],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "biased": {{
        "count": <int, 편향 표현이 포함된 문장 개수>,
        "detected_examples": [],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "slang": {{
        "count": <int, 비표준어가 포함된 문장 개수>,
        "detected_examples": [2],
        "reason": "<판단 근거>",
        "improvement": "<개선 방법>"
    }},
    "summary": "<종합 요약 3-4문장>",
    "advice": "<개선 조언 3-4문장>",
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
화자의 발화를 분석하여 발화 속도, 발음, 의미 명료도, 침묵 패턴, 말 끊기, 욕설, 군말/망설임, 편향, 비표준어 등을 평가하고 구조화된 피드백을 제공합니다.
타임스탬프 정보를 활용하여 정량적 지표를 계산하고, 텍스트 분석을 통해 정성적 평가를 수행합니다.
항상 JSON 형식으로만 응답하며, 객관적이고 구체적인 조언을 제공합니다.
detected_examples에는 반드시 Sentence 인덱스 번호(정수)만 반환해야 하고, sentence_feedbacks에는 각 문장별 간결한 피드백 메시지를 제공해야 합니다.

허용되는 category 값: speaking_speed, silence, clarity, meaning_clarity, cut, curse, filler, biased, slang"""
