from pydub import AudioSegment
from io import BytesIO
from typing import Tuple
import os
import platform
from pathlib import Path


# 환경에 따라 ffmpeg 경로 자동 설정
def setup_ffmpeg():
    system = platform.system()

    if system == "Windows":
        # 1순위: 프로젝트 루트의 ffmpeg 폴더 (배포용)
        project_root = Path(__file__).parent.parent.parent  # app/service -> app -> 프로젝트 루트
        project_ffmpeg = project_root / "ffmpeg" / "bin" / "ffmpeg.exe"
        project_ffprobe = project_root / "ffmpeg" / "bin" / "ffprobe.exe"
        
        # 2순위: 시스템에 설치된 ffmpeg (로컬 개발용)
        system_ffmpeg = Path(r"C:\ffmpeg-2025-12-01-git-7043522fe0-full_build\ffmpeg-2025-12-01-git-7043522fe0-full_build\bin\ffmpeg.exe")
        system_ffprobe = Path(r"C:\ffmpeg-2025-12-01-git-7043522fe0-full_build\ffmpeg-2025-12-01-git-7043522fe0-full_build\bin\ffprobe.exe")
        
        if project_ffmpeg.exists():
            AudioSegment.converter = str(project_ffmpeg)
            AudioSegment.ffmpeg = str(project_ffmpeg)
            AudioSegment.ffprobe = str(project_ffprobe)
            print(f"ffmpeg 경로 설정 완료 (프로젝트): {project_ffmpeg}")
        elif system_ffmpeg.exists():
            AudioSegment.converter = str(system_ffmpeg)
            AudioSegment.ffmpeg = str(system_ffmpeg)
            AudioSegment.ffprobe = str(system_ffprobe)
            print(f"ffmpeg 경로 설정 완료 (시스템): {system_ffmpeg}")
        else:
            print("Warning: Windows ffmpeg 경로를 찾을 수 없습니다.")
            print(f"  - 프로젝트 경로 확인: {project_ffmpeg}")
            print(f"  - 시스템 경로 확인: {system_ffmpeg}")

    # EC2/Docker 환경 - PATH에서 자동으로 찾음
    elif system == "Linux":
        # 프로젝트 루트의 ffmpeg 확인 (Docker 배포용)
        project_root = Path(__file__).parent.parent.parent
        project_ffmpeg = project_root / "ffmpeg" / "ffmpeg"
        project_ffprobe = project_root / "ffmpeg" / "ffprobe"
        
        if project_ffmpeg.exists():
            AudioSegment.converter = str(project_ffmpeg)
            AudioSegment.ffmpeg = str(project_ffmpeg)
            AudioSegment.ffprobe = str(project_ffprobe)
            print(f"ffmpeg 경로 설정 완료 (프로젝트): {project_ffmpeg}")
        else:
            # apt-get install ffmpeg로 설치되면 /usr/bin/ffmpeg에 위치
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
                "프로젝트 루트에 ffmpeg/bin/ffmpeg.exe를 배치하거나, "
                "시스템에 ffmpeg를 설치하세요."
            )
        except Exception as e:
            raise RuntimeError(f"오디오 변환 중 오류 발생: {str(e)}")