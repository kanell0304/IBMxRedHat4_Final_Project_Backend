# 음성 분석 백엔드 서버
## 환경 설정

### 1. Conda 환경 생성
```bash
conda create -n TeamProjectBackend python=3.10
conda activate TeamProjectBackend
```

### 2. 패키지 설치
**install.bat** 파일을 생성하고 실행:
```bat
@echo off
echo 패키지 설치 시작...

echo [1/7] NumPy 설치 (버전 제한 중요)
pip uninstall numpy -y
pip install "numpy<2.0"

echo [2/7] 기본 ML 패키지 설치
pip install scikit-learn pandas

echo [3/7] 오디오 처리 패키지 설치
pip install librosa pydub

echo [4/7] PyTorch 설치 (CPU 버전)
pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu

echo [5/7] Transformers 설치
pip install transformers==4.39.3

echo [6/7] 나머지 패키지 설치
pip install -r requirements.txt

echo [7/7] NumPy 버전 최종 확인
python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"

echo 설치 완료!
pause
```

실행:
```bash
install.bat
```

#### 수동 설치
```bash
# 1. NumPy 먼저 설치 (반드시 2.0 미만 버전)
pip uninstall numpy -y
pip install "numpy<2.0"

# 2. 기본 ML 패키지 설치
pip install scikit-learn
pip install pandas

# 3. 오디오 처리 패키지 설치
pip install librosa
pip install pydub

# 4. PyTorch 및 관련 패키지 설치 (CPU 버전)
pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu

# 5. Transformers 설치
pip install transformers==4.39.3

# 6. 나머지 패키지 일괄 설치
pip install -r requirements.txt

# 7. NumPy 버전 확인 (1.26.x 여야 함)
python -c "import numpy; print(f'NumPy version: {numpy.__version__}')"
```

### 3. ffmpeg 설치 (Windows)

MP3 등 다양한 오디오 포맷을 WAV로 변환하기 위해 필요합니다.

1. https://github.com/BtbN/FFmpeg-Builds/releases 접속
2. `ffmpeg-master-latest-win64-gpl.zip` 다운로드
3. `C:\ffmpeg\` 폴더에 압축 해제
4. 최종 경로 확인: `C:\ffmpeg\bin\ffmpeg.exe`

### 4. 설치 확인
```bash
# 각 패키지 import 테스트
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "import sklearn; print('scikit-learn: OK')"
python -c "import librosa; print('librosa: OK')"
python -c "import torch; print('torch: OK')"
python -c "import torchaudio; print('torchaudio: OK')"
python -c "import transformers; print('transformers: OK')"
```

모든 패키지가 정상적으로 import되면 설치 완료입니다.

### 5. 서버 실행
```bash
python -m uvicorn main:app --port=8081 --reload
```

서버가 정상적으로 시작되면:
- API 문서: http://127.0.0.1:8081/docs
- 헬스체크: http://127.0.0.1:8081/voice/health

---

## 주의사항

### ⚠중요: NumPy 버전
- **반드시 NumPy 2.0 미만 버전**을 사용해야 합니다
- NumPy 2.x는 PyTorch 2.1.0과 호환되지 않습니다
- 설치 중 NumPy가 자동으로 업그레이드되면 다시 다운그레이드하세요:
```bash
  pip uninstall numpy -y
  pip install "numpy<2.0"
```

### 패키지 설치 순서
1. NumPy (가장 먼저)
2. scikit-learn, pandas
3. librosa, pydub
4. PyTorch (CPU 버전, 별도 인덱스 사용)
5. transformers
6. 나머지 패키지

이 순서를 지키지 않으면 바이너리 호환성 문제가 발생할 수 있습니다.

---

## 트러블슈팅

### NumPy 관련 오류

**오류 메시지:**
```
NumPy 2.2.6 cannot be run... downgrade to 'numpy<2'
```

**해결 방법:**
```bash
pip uninstall numpy -y
pip install "numpy<2.0"
python -m uvicorn main:app --port=8081 --reload
```

### ffmpeg 관련 경고

**경고 메시지:**
```
Couldn't find ffmpeg or avconv
```

**해결 방법:**
1. ffmpeg가 `C:\ffmpeg\bin\ffmpeg.exe`에 설치되어 있는지 확인
2. 서버를 재시작

### 모듈을 찾을 수 없는 오류
```bash
# 누락된 패키지 확인 후 설치
pip install [패키지명]
```

---

## 지원하는 오디오 포맷

- .wav (변환 없이 직접 처리)
- .mp3
- .m4a
- .ogg
- .flac
- .aac
- .wma

모든 포맷은 자동으로 16kHz 모노 WAV로 변환되어 분석됩니다.