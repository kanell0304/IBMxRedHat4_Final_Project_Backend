from google.cloud import speech_v2
from google.cloud.speech_v2 import types
from typing import Dict, Any
import json

location = "us"  # chirp_3와 long 모델 같이 사용 가능한 리전
client = speech_v2.SpeechClient(client_options={"api_endpoint": f"{location}-speech.googleapis.com"})

class STTService:

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = client

    # chirp 모델 (화자분리)
    async def transcribe_chirp(self, wav_data: bytes) -> Dict[str, Any]:

        # 모델 설정
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

        # STT 요청 생성
        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{location}/recognizers/chirp",
            config=config,
            content=wav_data,  
        )

        # Google STT API 호출
        response = self.client.recognize(request=request)

        # 결과 포맷 초기화
        result = {
            "results": [],
            "languageCode": "ko-KR"
        }

        # 응답 데이터 변환
        for res in response.results:
            if res.alternatives:
                alt = res.alternatives[0]
                result["results"].append({
                    "alternatives": [{
                        "transcript": alt.transcript,  # 변환된 텍스트 (문장 단위)
                        "words": [
                            {
                                "word": word.word,  
                                "speakerLabel": str(word.speaker_label) if hasattr(word, 'speaker_label') else "1"  # 화자 번호 없으면 1로
                            }
                            for word in alt.words
                        ]
                    }]
                })

        return result
    
    # long 모델 (타임스탬프)
    async def transcribe_long(self, wav_data: bytes) -> Dict[str, Any]:

        # 모델 설정
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(), 
            language_codes=["ko-KR"], 
            model="long",  
            features=speech_v2.RecognitionFeatures(
                enable_word_time_offsets=True,  # 단어별 시작/끝 시간 포함
            ),
        )

        # STT 요청 생성
        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{location}/recognizers/long",
            config=config,
            content=wav_data, 
        )

        # Google STT API 호출
        response = self.client.recognize(request=request)

        # 결과 포맷 초기화
        result = {
            "results": []
        }

        # 응답 데이터 변환
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