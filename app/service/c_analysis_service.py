from typing import Dict
from app.service.c_bert_service import get_inference_service
from app.service.llm.openai_service import OpenAIService
from app.service.llm.watsonx_service import WatsonxService
from app.service.script_parser import get_script_parser
from app.core.settings import settings


class CAnalysisService:

    def __init__(self):
        self.bert_service = get_inference_service()  # c_bert inference service 가져옴
        self.llm_service = self.get_llm_service()  # LLM_PROVIDER 보고 서비스 결정
        self.script_parser = get_script_parser()  # script parser 가져옴

    def get_llm_service(self):
        if settings.llm_provider == "openai":
            return OpenAIService()
        elif settings.llm_provider == "watsonx":
            return WatsonxService()
        else:
            raise ValueError(f"지원하지 않는 LLM_PROVIDER : {settings.llm_provider}")

    def extract_target_speaker_text(self, stt_data: Dict, target_speaker: str) -> str:
        words = []

        if "results" not in stt_data:
            return ""

        for result in stt_data["results"]:
            if "alternatives" not in result or len(result["alternatives"]) == 0:
                continue

            alt = result["alternatives"][0]

            if "words" not in alt:
                continue

            # target_speaker의 단어만 필터링
            speaker_words = [
                word["word"]
                for word in alt["words"]
                if word.get("speakerLabel", "1") == target_speaker
            ]

            words.extend(speaker_words)

        return " ".join(words)

    async def analyze_communication(
        self, stt_data: Dict, target_speaker: str = "1"
    ) -> Dict:

        # 1. STT 데이터를 문장 단위로 파싱
        sentences = self.script_parser.parse_sentences_from_stt(stt_data)

        if not sentences:
            raise ValueError("STT 결과에서 문장을 파싱할 수 없습니다.")

        # 2. target_speaker의 발화만 추출
        target_text = self.extract_target_speaker_text(stt_data, target_speaker)

        if not target_text.strip():
            raise ValueError(
                f"{target_speaker}를 찾을 수 없습니다"
            )

        # 3. BERT 멀티 라벨 분류
        bert_result = self.bert_service.predict_labels(target_text)

        # 4. LLM report 생성 (communication_prompts 사용)
        from app.prompts.communication_prompts import build_prompt, SYSTEM_MESSAGE
        import json

        # sentences와 stt_data 모두 전달 (단어 단위 타임스탬프 분석용)
        prompt = build_prompt(sentences, stt_data, bert_result, target_speaker)

        # OpenAI 호출
        if isinstance(self.llm_service, OpenAIService):
            response = await self.llm_service.client.chat.completions.create(
                model=self.llm_service.model,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            llm_result = json.loads(response.choices[0].message.content)
        else:
            # Watsonx 등 다른 LLM service 사용 시
            raise NotImplementedError("Watsonx는 아직 구현되지 않았습니다.")

        return {
            "sentences": sentences,
            "bert_result": bert_result,
            "llm_result": llm_result,
        }


# 싱글턴 인스턴스
c_analysis_service = None


def get_c_analysis_service():
    global c_analysis_service
    if c_analysis_service is None:
        c_analysis_service = CAnalysisService()
    return c_analysis_service
