from pydub import AudioSegment
from io import BytesIO
from typing import Tuple

# 음성 파일 WAV 변환 

class AudioService:
    @staticmethod
    def convert_to_wav(audio_data: bytes, original_format: str) -> Tuple[bytes, float]:
        # audio_data: 원본 오디오 바이너리 데이터
        # original_format: 원본 포맷 (mp3, m4a, wav, webm 등)
        
        audio = AudioSegment.from_file(
            BytesIO(audio_data), 
            format=original_format
        )
        
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        
        wav_buffer = BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_data = wav_buffer.getvalue()
        
        duration = len(audio) / 1000.0
        
        return wav_data, duration