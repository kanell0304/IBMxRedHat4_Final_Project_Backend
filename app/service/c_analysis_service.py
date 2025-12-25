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

        # [CRITICAL] BERT/Rule-based 결과를 Truth로 간주하여 LLM 결과 덮어쓰기
        # LLM이 엉뚱한 문장을 욕설로 잡거나(환각), 잡아야 할 문장을 놓치는 것을 방지
        
        # 1. 카테고리별 detected_examples 강제 동기화
        target_categories = ["curse", "biased", "filler"]
        
        # 초기화 (LLM 결과 싹 비우고 BERT 결과로 채움)
        for cat in target_categories:
            if cat not in llm_result:
                llm_result[cat] = {"reason": "감지된 내용이 없습니다.", "improvement": "", "detected_examples": []}
            else:
                llm_result[cat]["detected_examples"] = []

        # BERT 결과 주입
        for idx, issues in bert_sentence_results.items():
            for issue in issues:
                # issue 문자열(예: 'curse', 'biased')이 target_categories에 있다면 추가
                if issue in target_categories:
                    if idx not in llm_result[issue]["detected_examples"]:
                        llm_result[issue]["detected_examples"].append(idx)
                # 'slang'은 'curse'로 통합 처리
                elif issue == 'slang':
                    if idx not in llm_result['curse']["detected_examples"]:
                        llm_result['curse']["detected_examples"].append(idx)

        # [CRITICAL] count 값 강제 동기화 (detected_examples 개수와 일치)
        # 프론트엔드 그래프 및 요약 통계의 정합성을 보장
        for cat in target_categories:
            if cat in llm_result:
                llm_result[cat]["count"] = len(llm_result[cat]["detected_examples"])

        # 2. sentence_feedbacks 강제 동기화
        if "sentence_feedbacks" not in llm_result:
            llm_result["sentence_feedbacks"] = []
            
        # 기존 피드백 맵핑 생성 (curse/biased/filler 제외한 나머지만 유지)
        clean_feedbacks = {}
        for item in llm_result["sentence_feedbacks"]:
            idx = item["sentence_index"]
            # 해당 카테고리가 아닌 것들만 남김 (예: speed, clarity 등은 유지)
            filtered_fbs = [
                fb for fb in item.get("feedbacks", []) 
                if fb.get("category") not in target_categories and fb.get("category") != 'slang'
            ]
            if filtered_fbs:
                clean_feedbacks[idx] = filtered_fbs

        # BERT 결과로 피드백 재생성
        for idx, issues in bert_sentence_results.items():
            if idx not in clean_feedbacks:
                clean_feedbacks[idx] = []
            
            for issue in issues:
                category = issue
                message = f"{issue} 감지됨"
                
                if issue == 'curse' or issue == 'slang':
                    category = 'curse'
                    message = "욕설/비속어 사용"
                elif issue == 'biased':
                    category = 'biased'
                    message = "차별/비하 발언 감지"
                elif issue == 'filler':
                    category = 'filler'
                    message = "습관어(추임새) 사용"

                # 중복 추가 방지
                if not any(fb["category"] == category for fb in clean_feedbacks[idx]):
                    clean_feedbacks[idx].append({"category": category, "message": message})

        # 리스트 형태로 변환하여 할당
        llm_result["sentence_feedbacks"] = [
            {"sentence_index": idx, "feedbacks": fbs} 
            for idx, fbs in clean_feedbacks.items()
            if fbs # 피드백이 있는 경우만
        ]

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
