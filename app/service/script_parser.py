from typing import Dict, List
import re

# communication에서 스크립트 문장 단위로 나눠서 저장하는 용

class ScriptParser:

    def __init__(self):
        self.sentence_endings = re.compile(r'[.!?]\s+|[.!?]$') # 한국어 문장 종결 패턴

    def parse_sentences_from_stt(self, stt_data: Dict) -> List[Dict]:
        sentences = []
        sentence_index = 0

        if "results" not in stt_data:
            return sentences

        current_speaker = None
        current_words = []
        current_text = ""

        for result in stt_data["results"]:
            if "alternatives" not in result or len(result["alternatives"]) == 0:
                continue

            alt = result["alternatives"][0]

            if "words" not in alt:
                continue

            for word_info in alt["words"]:
                speaker = word_info.get("speakerLabel", "1")
                word = word_info.get("word", "")
                start_time = word_info.get("startTime", "0s")
                end_time = word_info.get("endTime", "0s")

                # 화자가 바뀌면 이전 내용을 문장으로 분리
                if current_speaker is not None and current_speaker != speaker:
                    # 현재까지 모은 내용을 문장으로 분리
                    if current_text.strip():
                        parsed_sentences = self._split_into_sentences(
                            current_text, current_words, current_speaker
                        )
                        for sent in parsed_sentences:
                            sent["sentence_index"] = sentence_index
                            sentences.append(sent)
                            sentence_index += 1

                    # 초기화
                    current_words = []
                    current_text = ""

                # 현재 화자 설정
                current_speaker = speaker
                current_words.append(
                    {
                        "word": word,
                        "start_time": start_time,
                        "end_time": end_time,
                    }
                )
                current_text += word + " "

        # 마지막 남은 내용 처리
        if current_text.strip():
            parsed_sentences = self._split_into_sentences(
                current_text, current_words, current_speaker
            )
            for sent in parsed_sentences:
                sent["sentence_index"] = sentence_index
                sentences.append(sent)
                sentence_index += 1

        return sentences

    def _split_into_sentences(
        self, text: str, words: List[Dict], speaker: str
    ) -> List[Dict]:
        sentences = []

        text = text.strip()
        parts = re.split(r'([.!?])\s*', text)

        current_sentence = ""
        word_idx = 0
        sentence_start_idx = 0

        for i, part in enumerate(parts):
            if not part.strip():
                continue

            current_sentence += part

            # 문장 종결 기호인 경우
            if part in ['.', '!', '?']:
                # 현재 문장에 해당하는 단어들 찾기
                word_count = len(current_sentence.split())
                sentence_words = words[sentence_start_idx : sentence_start_idx + word_count]

                if sentence_words:
                    sentences.append(
                        {
                            "speaker_label": speaker,
                            "text": current_sentence.strip(),
                            "start_time": sentence_words[0]["start_time"],
                            "end_time": sentence_words[-1]["end_time"],
                        }
                    )

                # 초기화
                current_sentence = ""
                sentence_start_idx += word_count

        # 남은 내용 (문장 종결어미 없이 끝난 경우)
        if current_sentence.strip():
            remaining_words = words[sentence_start_idx:]
            if remaining_words:
                sentences.append(
                    {
                        "speaker_label": speaker,
                        "text": current_sentence.strip(),
                        "start_time": remaining_words[0]["start_time"],
                        "end_time": remaining_words[-1]["end_time"],
                    }
                )

        # 문장이 하나도 없으면 전체를 하나의 문장으로
        if not sentences and text.strip() and words:
            sentences.append(
                {
                    "speaker_label": speaker,
                    "text": text.strip(),
                    "start_time": words[0]["start_time"],
                    "end_time": words[-1]["end_time"],
                }
            )

        return sentences


# 싱글턴
_script_parser = None


def get_script_parser():
    global _script_parser
    if _script_parser is None:
        _script_parser = ScriptParser()
    return _script_parser
