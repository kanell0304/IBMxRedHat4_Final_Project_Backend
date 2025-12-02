from google.cloud import speech_v2
from google.cloud.speech_v2 import types
from typing import Dict, Any
import json

# ===== Google Cloud Speech-to-Text 서비스 =====

# 0. 필요한 변수들 정의
location = "us"  # chirp_3와 long 모델 같이 사용 가능한 리전
client = speech_v2.SpeechClient(client_options={"api_endpoint": f"{location}-speech.googleapis.com"})

class STTService:

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = client

    async def transcribe_chirp(self, wav_data: bytes) -> Dict[str, Any]:

        config = types.RecognitionConfig(
            auto_decoding_config=types.AutoDetectDecodingConfig(), 
            language_codes=["ko-KR"],  
            model="chirp_3", 
            features=types.RecognitionFeatures(
                diarization_config=types.SpeakerDiarizationConfig(
                    min_speaker_count=2,   
                    max_speaker_count=3, 
                )                
            ),
        )

        # 1-2. STT 요청 생성
        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{location}/recognizers/chirp",
            config=config,
            content=wav_data,  # WAV 파일 바이너리 데이터
        )

        # 1-3. Google STT API 호출
        response = self.client.recognize(request=request)

        # 1-4. 결과 포맷 초기화
        result = {
            "results": [],
            "languageCode": "ko-KR"
        }

        # 1-5. 응답 데이터를 결과 포맷으로 변환
        for res in response.results:
            if res.alternatives:
                alt = res.alternatives[0]
                result["results"].append({
                    "alternatives": [{
                        "transcript": alt.transcript,  # 변환된 텍스트
                        "words": [
                            {
                                "word": word.word,  # 단어
                                "speakerLabel": str(word.speaker_label) if hasattr(word, 'speaker_label') else "1"  # 화자 번호
                            }
                            for word in alt.words
                        ]
                    }]
                })

        return result
    
    # 2. transcribe_long: long 모델로 상세 텍스트 + 타임스탬프 + 신뢰도
    async def transcribe_long(self, wav_data: bytes) -> Dict[str, Any]:
        # 2-1. Long 모델 설정 (상세 텍스트 + 단어별 타임스탬프 + 신뢰도)
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),  # 자동 오디오 포맷 인식
            language_codes=["ko-KR"],  # 한국어 설정
            model="long",  # Long 모델 사용 (긴 오디오에 최적화)
            features=speech_v2.RecognitionFeatures(
                enable_word_time_offsets=True,  # 단어별 시작/끝 시간 포함
            ),
        )

        # 2-2. STT 요청 생성
        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{location}/recognizers/long",
            config=config,
            content=wav_data,  # WAV 파일 바이너리 데이터
        )

        # 2-3. Google STT API 호출
        response = self.client.recognize(request=request)

        # 2-4. 결과 포맷 초기화
        result = {
            "results": []
        }

        # 2-5. 응답 데이터를 결과 포맷으로 변환
        for res in response.results:
            if res.alternatives:
                alt = res.alternatives[0]
                result["results"].append({
                    "alternatives": [{
                        "transcript": alt.transcript,  # "transcript": " 아니 그거 있잖아 그 내가 저번에 말했던 거"
                        "confidence": alt.confidence,  # "confidence": 0.8704867362976074, 
                        "words": [                     # {"words": [{"word": "▁아니", "endTime": "13.000s", "startTime": "12.000s", "confidence": 0.8704867362976074}, { ...
                            {
                                "word": word.word,  
                                "startTime": f"{word.start_offset.seconds}.{word.start_offset.microseconds // 1000:03d}s",  
                                "endTime": f"{word.end_offset.seconds}.{word.end_offset.microseconds // 1000:03d}s",  
                            }
                            for word in alt.words
                        ]
                    }]
                })

        return result