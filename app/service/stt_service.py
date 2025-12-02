from google.cloud import speech_v2
from typing import Dict, Any
import json

# Google STT 연결

# chirp 사용 가능한 리전 지정
location = "us" 
client = speech_v2.SpeechClient(client_options={"api_endpoint": f"{location}-speech.googleapis.com"})

class STTService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = client
    
    async def transcribe_chirp(self, wav_data: bytes) -> Dict[str, Any]:
        # Chirp 모델로 화자분리
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=["ko-KR"],
            model="chirp_3",
            features=speech_v2.RecognitionFeatures(
                enable_word_time_offsets=True
            ),
        )
        
        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{location}/recognizers/chirp",
            config=config,
            content=wav_data,
        )
        
        response = self.client.recognize(request=request)
        
        result = {
            "results": [],
            "languageCode": "ko-KR"
        }
        
        for res in response.results:
            if res.alternatives:
                alt = res.alternatives[0]
                result["results"].append({
                    "alternatives": [{
                        "transcript": alt.transcript,
                        "words": [
                            {
                                "word": word.word,
                                "speakerLabel": str(word.speaker_label) if hasattr(word, 'speaker_label') else "1"
                            }
                            for word in alt.words
                        ]
                    }]
                })
        
        return result
    
    async def transcribe_long(self, wav_data: bytes) -> Dict[str, Any]:
        # Long 모델로 상세 텍스트 + 타임스탬프
        
        config = speech_v2.RecognitionConfig(
            auto_decoding_config=speech_v2.AutoDetectDecodingConfig(),
            language_codes=["ko-KR"],
            model="long",
            features=speech_v2.RecognitionFeatures(
                enable_word_time_offsets=True,
                enable_word_confidence=True
            ),
        )
        
        request = speech_v2.RecognizeRequest(
            recognizer=f"projects/{self.project_id}/locations/{location}/recognizers/long",
            config=config,
            content=wav_data,
        )
        
        response = self.client.recognize(request=request)
        
        result = {
            "results": []
        }
        
        for res in response.results:
            if res.alternatives:
                alt = res.alternatives[0]
                result["results"].append({
                    "alternatives": [{
                        "transcript": alt.transcript,
                        "confidence": alt.confidence,
                        "words": [
                            {
                                "word": word.word,
                                "startTime": f"{word.start_offset.seconds}.{word.start_offset.microseconds // 1000:03d}s",
                                "endTime": f"{word.end_offset.seconds}.{word.end_offset.microseconds // 1000:03d}s",
                                "confidence": word.confidence
                            }
                            for word in alt.words
                        ]
                    }]
                })
        
        return result