import whisper
import numpy as np
from typing import Dict, Any



whisper_model=None

def get_whisper_model(model_name:str="base"):
    global whisper_model
    if whisper_model is None:
        print(f"[Whisper] 모델 '{model_name}' 로딩중...")
        whisper_model=whisper.load_model(model_name)
        print(f"[Whisper] 모델 로드 완료!")
    return whisper_model


class WhisperSTTService:
    def __init__(self, model_name:str="base"):
        self.model=get_whisper_model(model_name)

    # 영어 음성을 텍스트로 변환
    async def transcribe_english(self, wav_data:bytes)->Dict[str, Any]:
        import io
        from pydub import AudioSegment
        audio=AudioSegment.from_file(io.BytesIO(wav_data), format="wav")
        samples=np.array(audio.get_array_of_samples()).astype(np.float32)/32768.0

        # whisper 실행
        result=self.model.transcribe(
            samples,
            language="en",
            word_timestamps=True,
            verbose=False,
        )

        # Google STT 형식 변환
        formatted_result={
            "results":[]
        }

        if result.get("segments"):
            for segment in result["segments"]:
                word_list=[]

                if segment.get("words"):
                    for word_info in segment["words"]:
                        word_list.append({
                            "word":word_info.get("word", "").strip(),
                            "startTime":f"{word_info.get('start', 0):.3f}s",
                            "endTime":f"{word_info.get('end', 0):.3f}s",
                            "confidence":word_info.get("probability", 0.9)
                        })

                formatted_result["results"].append({
                    "alternatives":[{
                        "transcript":segment.get("text", "").strip(),
                        "words":word_list
                    }]
                })

        return formatted_result
    




