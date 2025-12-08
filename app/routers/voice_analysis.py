from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import tempfile
import os

# ffmpeg 경로 설정 -> 현재 c:/ffmpeg 폴더 안에 있음
os.environ["PATH"] = r"C:\ffmpeg\bin" + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment

# pydub에 ffmpeg 경로 명시적으로 지정
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

# ffmpeg 존재 확인
if not os.path.exists(AudioSegment.converter):
    print(f"\n[WARNING] ffmpeg를 찾을 수 없습니다: {AudioSegment.converter}")
    print("MP3, M4A 등의 파일 변환이 실패할 수 있습니다.\n")
else:
    print(f"[OK] ffmpeg 발견: {AudioSegment.converter}")

from ..service.voice_analyzer import get_analyzer

router = APIRouter(prefix="/voice", tags=["voice-analysis"])

# 발표 녹음 파일 분석
@router.post("/analyze")
async def analyze_voice(audio_file: UploadFile = File(..., description="음성 파일 (.wav, .mp3, .m4a, .ogg 등)"), estimated_syllables: Optional[int] = Form(None, description="추정 음절 수 (선택사항)")):
    supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac', '.wma']

    file_extension = os.path.splitext(audio_file.filename)[1].lower()
    if file_extension not in supported_formats:
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Supported formats: {', '.join(supported_formats)}")

    temp_input_file = None
    temp_wav_file = None

    try:
        print(f"1. 업로드된 파일: {audio_file.filename}")
        print(f"2. 파일 확장자: {file_extension}")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
            contents = await audio_file.read()
            tmp.write(contents)
            temp_input_file = tmp.name
        
        print(f"3. 임시 파일 저장: {temp_input_file}")
        print(f"4. 파일 존재 확인: {os.path.exists(temp_input_file)}")

        if file_extension != '.wav':
            print("5. WAV 변환 시작...")
            temp_wav_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name

            audio = AudioSegment.from_file(temp_input_file)
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            audio.export(temp_wav_file, format="wav")
            
            print(f"6. WAV 변환 완료: {temp_wav_file}")
            analysis_file = temp_wav_file
        else:
            print("5. WAV 파일이므로 변환 스킵")
            analysis_file = temp_input_file
        
        print(f"7. 분석 파일: {analysis_file}")

        analyzer = get_analyzer()
        result = analyzer.analyze(audio_path=analysis_file, estimated_syllables=estimated_syllables)

        if "error" in result:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {result['error']}")

        return JSONResponse(content={"success": True, "data": result})

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n=== 오류 발생 ===")
        print(error_trace)
        print(f"=================\n")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        for temp_file in [temp_input_file, temp_wav_file]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass

# 서버 상태 확인
@router.get("/health")
async def health_check():
    try:
        analyzer = get_analyzer() # 분석 기능 불러오기
        return {
            "status": "ok", # 상태
            "analyzer": "loaded", # 분석 모델 로딩 상태
            "device": str(analyzer.device), # 작동 장치 종류
            "emotions": list(analyzer.idx_to_emotion.values()) # 어떤 감정들을 분석 가능한지
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
