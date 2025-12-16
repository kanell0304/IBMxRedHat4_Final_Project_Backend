from pydub import AudioSegment
from io import BytesIO
from typing import Tuple
import os

# wav외 다른 포맷들 처리하려면 ffmpeg 다운받아야 된다고 해서 다운받고 경로 설정했는데도 오류납니다 
# 일단 wav만 넣어서 테스트해주세요

AudioSegment.converter = r"C:\ffmpeg-2025-12-01-git-7043522fe0-full_build\ffmpeg-2025-12-01-git-7043522fe0-full_build\bin"

class AudioService:
    @staticmethod
    def convert_to_wav(audio_data: bytes, original_format: str) -> Tuple[bytes, float]:
        try:
            if original_format.startswith('.'):
                original_format = original_format[1:]

            original_format = original_format.lower()

            format_mapping = {
                'mp3': 'mp3',
                'm4a': 'mp4',
                'mp4': 'mp4',
                'webm': 'webm',
                'ogg': 'ogg',
                'wav': 'wav',
                'flac': 'flac',
                'aac': 'aac'
            }

            format_to_use = format_mapping.get(original_format, original_format)

            audio = AudioSegment.from_file(
                BytesIO(audio_data),
                format=format_to_use
            )

            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

            wav_buffer = BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_data = wav_buffer.getvalue()

            duration = len(audio) / 1000.0

            return wav_data, duration

        except FileNotFoundError as e:
            raise RuntimeError(
                "ffmpeg 오류"
            )
        except Exception as e:
            raise RuntimeError(f"오디오 변환 중 오류 발생: {str(e)}")