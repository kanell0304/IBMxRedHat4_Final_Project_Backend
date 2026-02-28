import time
import tracemalloc
import statistics
import sys
import tempfile
import json
import os
os.environ["PATH"] = r"C:\ffmpeg\bin" + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment
AudioSegment.converter = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffmpeg = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.service.voice_analyzer import get_analyzer
from app.service.audio_service import AudioService

AUDIO_FILE = "테스트용 강연 파일 6분.mp3"
REPEAT = 3 # 반복 횟수(평균값 계산을 위해)


def measure_single_run(wav_path: str) -> dict:
    analyzer = get_analyzer()

    tracemalloc.start()
    timings = {}

    t0 = time.perf_counter()
    wav2vec_features = analyzer.extract_wav2vec_features(wav_path)
    timings["wav2vec_sec"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    speech_features = analyzer.analyze_speech_features(wav_path)
    timings["librosa_sec"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    result = analyzer.analyze(wav_path)
    timings["total_sec"] = time.perf_counter() - t0

    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    timings["peak_memory_mb"] = peak_memory / 1024 / 1024

    return timings


def run_benchmark(label: str, audio_path: str, repeat: int = REPEAT):
    print(f"{label}")
    print(f"파일: {audio_path}")
    print(f"반복 횟수: {repeat}회")

    # 음성파일 컨버터(wav로 변환한 후 진행)
    print("\n[전처리] m4a → wav 변환 중...")
    ext = os.path.splitext(audio_path)[1]
    with open(audio_path, "rb") as f:
        audio_data = f.read()
    wav_data, duration = AudioService.convert_to_wav(audio_data, ext)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(wav_data)
        temp_wav_path = tmp.name

    print(f"  변환 완료 - 길이: {duration:.1f}초 ({duration/60:.1f}분)")
    print(f"  임시 WAV: {temp_wav_path}")

    all_results = []

    try:
        for i in range(repeat):
            print(f"\n[{i + 1}/{repeat}] 측정 중 입니다...", end=" ", flush=True)
            result = measure_single_run(temp_wav_path)
            all_results.append(result)
            print(f"완료 ({result['total_sec']:.2f}초)")

        print(f"\n결과 요약")
        for key in ["wav2vec_sec", "librosa_sec", "total_sec", "peak_memory_mb"]:
            values = [r[key] for r in all_results]
            unit = "MB" if "memory" in key else "초"
            print(f"  {key:<20}: 평균 {statistics.mean(values):.2f}{unit} / "
                  f"최소 {min(values):.2f}{unit} / "
                  f"최대 {max(values):.2f}{unit}")
    finally:
        os.unlink(temp_wav_path)  # 임시 파일 정리

    return all_results


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "before"

    results = run_benchmark(
        label=f"[{label.upper()}] 청크 처리 {'미적용' if label == 'before' else '적용'}",
        audio_path=AUDIO_FILE,
    )

    output_path = f"benchmark_result_{label}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장됨: {output_path}")