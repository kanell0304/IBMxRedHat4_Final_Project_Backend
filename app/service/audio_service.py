from pydub import AudioSegment
from io import BytesIO
from typing import Tuple
import os
import platform


# 환경에 따라 ffmpeg 경로 자동 설정
def setup_ffmpeg():
    system = platform.system()

    # 로컬 Windows 환경
    if system == "Windows":
        ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe" # ffmpeg 실행파일 경로
        ffprobe_path = r"C:\ffmpeg\bin\ffprobe.exe"

        if os.path.exists(ffmpeg_path):
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffmpeg = ffmpeg_path
            AudioSegment.ffprobe = ffprobe_path
            print(f"ffmpeg 경로 설정 완료: {ffmpeg_path}")
        else:
            print("Warning: Windows ffmpeg 경로를 찾을 수 없습니다.")

    # EC2/Docker 환경 - PATH에서 자동으로 찾음
    # apt-get install ffmpeg로 설치되면 /usr/bin/ffmpeg에 위치
    # 별도 경로 설정 불필요
    elif system == "Linux":
        print("Linux 환경 감지: ffmpeg PATH 사용")


# 모듈 로드 시 자동 실행
setup_ffmpeg()


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
                "ffmpeg를 찾을 수 없습니다. "
                "Windows: C:\\ffmpeg\\bin\\ffmpeg.exe 확인, "
                "Linux: apt-get install ffmpeg 실행"
            )
        except Exception as e:
            raise RuntimeError(f"오디오 변환 중 오류 발생: {str(e)}")