from typing import Dict
from app.service.c_bert_service import get_inference_service
from app.service.llm_service import OpenAIService
from app.service.script_parser import get_script_parser
from app.core.settings import settings


class CAnalysisService:

    def __init__(self):
        self.bert_service = get_inference_service()  # c_bert inference service 가져옴
        self.llm_service = self.get_llm_service()  # LLM_PROVIDER 보고 서비스 결정
        self.script_parser = get_script_parser()  # script parser 가져옴

    def get_llm_service(self):
        provider = settings.llm_provider or "openai"
        if provider == "openai":
            return OpenAIService()
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

        # 3. BERT 멀티 라벨 분류 (문장별 분석)
        bert_sentence_results = {}
        total_counts = {"slang": 0, "biased": 0, "curse": 0, "filler": 0}

        for sent in sentences:
            if sent["speaker_label"] == target_speaker:
                # 문장별 예측
                labels = self.bert_service.predict_labels(sent["text"])
                
                # 감지된 라벨 수집
                detected = [k for k, v in labels.items() if v == 1]
                
                if detected:
                    bert_sentence_results[sent["sentence_index"]] = detected
                    
                    # 카운트 집계
                    for d in detected:
                        if d in total_counts:
                            total_counts[d] += 1

        # 전체 결과 (저장용)
        bert_result = total_counts.copy()
        
        # sentence_results도 함께 저장하고 싶다면 bert_result에 포함 (선택사항)
        bert_result["sentence_details"] = bert_sentence_results

        # 4. LLM report 생성 (communication_prompts 사용)
        from app.prompts.communication_prompts import build_prompt, SYSTEM_MESSAGE
        import json

        # sentences, stt_data, bert_result, bert_sentence_results 모두 전달
        prompt = build_prompt(sentences, stt_data, target_speaker, bert_result, bert_sentence_results)

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

        # [CRITICAL] BERT + LLM 융합: BERT가 감지한 것 100% 포함 + LLM 추가 감지도 유지
        # filler는 duration 기반으로 LLM이 독립 판단, 나머지는 BERT 강제 동기화

        # 1. 카테고리별 detected_examples BERT로 보강
        bert_sync_categories = ["curse", "biased", "slang"]  # filler 제외
        all_categories = ["curse", "biased", "filler", "slang"]

        # LLM 결과 없으면 초기화
        for cat in all_categories:
            if cat not in llm_result:
                llm_result[cat] = {"reason": "감지된 내용이 없습니다.", "improvement": "", "detected_examples": []}
            elif "detected_examples" not in llm_result[cat]:
                llm_result[cat]["detected_examples"] = []

        # BERT 결과 추가 (curse, biased, slang만 강제 동기화, filler는 LLM 독립 판단)
        for idx, issues in bert_sentence_results.items():
            for issue in issues:
                if issue in bert_sync_categories:
                    if idx not in llm_result[issue]["detected_examples"]:
                        llm_result[issue]["detected_examples"].append(idx)

        # 2. sentence_feedbacks BERT로 보강 (LLM 결과 유지 + BERT 추가)
        if "sentence_feedbacks" not in llm_result:
            llm_result["sentence_feedbacks"] = []

        # 기존 피드백 맵핑 생성 (LLM 결과 모두 유지)
        feedback_map = {}
        for item in llm_result["sentence_feedbacks"]:
            idx = item["sentence_index"]
            feedback_map[idx] = item.get("feedbacks", [])[:]  # 복사

        # BERT 결과 추가 (curse, biased, slang만, filler는 LLM 판단 우선)
        for idx, issues in bert_sentence_results.items():
            if idx not in feedback_map:
                feedback_map[idx] = []

            for issue in issues:
                # filler는 BERT 피드백 추가하지 않음 (LLM이 duration 기반으로 판단)
                if issue == 'filler':
                    continue

                category = issue
                message = f"{issue} 감지됨"

                if issue == 'curse':
                    message = "욕설/비속어 사용"
                elif issue == 'biased':
                    message = "차별/비하 발언 감지"
                elif issue == 'slang':
                    message = "비표준어 사용"

                # LLM이 이미 해당 카테고리 피드백 제공했으면 스킵
                if not any(fb["category"] == category for fb in feedback_map[idx]):
                    feedback_map[idx].append({"category": category, "message": message})

        # 리스트 형태로 변환
        llm_result["sentence_feedbacks"] = [
            {"sentence_index": idx, "feedbacks": fbs}
            for idx, fbs in feedback_map.items()
            if fbs
        ]

        # [CRITICAL] count 값 계산: sentence_feedbacks에서 실제 표시된 피드백 개수
        # 프론트엔드 스크립트 페이지의 이모지 개수와 그래프 count가 일치하도록 보장
        for cat in all_categories:
            if cat in llm_result:
                count = sum(
                    1 for item in llm_result.get("sentence_feedbacks", [])
                    for fb in item.get("feedbacks", [])
                    if fb.get("category") == cat
                )
                llm_result[cat]["count"] = count

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
