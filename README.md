<div align="center">

# 🎤 STEACH - Backend

### **"Your Personal Voice Coach - AI Engine"**

AI 기반 음성 분석 및 자연어 처리 백엔드 서버

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![AWS](https://img.shields.io/badge/AWS-EC2_S3_ECR-FF9900?style=flat-square&logo=amazon-aws)](https://aws.amazon.com/)

[Frontend Repository](https://github.com/kanell0304/IBMxRedHat4_Final_Project_Frontend)

</div>

---

## 📌 프로젝트 소개

**STEACH Backend**는 음성 인식, 자연어 처리, 감정 분석을 통합한 AI 기반 음성 코칭 API 서버입니다. Google Speech-to-Text, BERT, Wav2Vec2, OpenAI GPT 등 최신 AI 모델을 활용하여 종합적인 음성 분석 서비스를 제공합니다.

### 🎯 해결하고자 한 문제

| 문제점                 | 솔루션                                   |
|---------------------|---------------------------------------|
| 음성 데이터의 실시간 처리 및 분석 | 비동기 처리 기반 FastAPI로 높은 처리량 보장          |
| 다양한 AI 모델의 효율적 통합   | 모듈화된 서비스 레이어 아키텍처                     |
| 대용량 ML 모델의 배포 및 관리  | AWS S3/HuggingFace 기반 모델 저장 및 자동 다운로드 |
| 안정적인 서버 배포 자동화      | Docker 컨테이너화 및 GitHub Actions CI/CD   |

---

## ✨ 주요 기능

### 🎙️ 음성-텍스트 변환 (STT)
**Google Speech-to-Text API**
- 실시간 음성 인식 및 텍스트 변환
- 화자 분리 (Diarization) 지원
- 한국어/영어 다국어 지원
- 긴 음성 파일 처리 (최대 1시간)

**OpenAI Whisper (대체 엔진)**
- 오프라인 환경 지원
- 높은 정확도 (특히 잡음 환경)

### 🧠 자연어 처리 (NLP)
**BERT 기반 부적절 표현 감지**
- 한국어 사전 학습 모델 (KoBERT)
- 문장 단위 분류 (부적절 표현 스코어링)
- 컨텍스트 기반 분석

**OpenAI GPT 피드백 생성**
- 맞춤형 코칭 메시지 자동 생성
- 구체적인 개선 제안
- 긍정적이고 격려하는 톤

### 📊 음성 특징 분석
**Librosa 기반 음향 분석**
- 말하기 속도 (Speech Rate): 분당 단어 수
- 발화 속도 (Articulation Rate): 순수 말하기 속도
- 억양 변화 (Pitch Variation): 음높이 표준편차
- 음높이 범위 (Pitch Range): 최대-최소 주파수

**수치 정규화 및 점수화**
- 0-100점 척도 변환
- 기준치 기반 등급 산정 (우수/보통/개선 필요)

### 🎭 감정 분석
**Wav2Vec2 + SVM 감정 분류**
- 음성 벡터 임베딩 추출 (Wav2Vec2 XLSR-300M)
- 42GB 한국어 감정 음성 데이터셋 학습 
- 데이터 셋 출처: https://aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&dataSetSn=466
- 6개 감정 클래스 분류
- **정확도: 84.38%**

**지원 감정 카테고리**
- 분노 (Angry)
- 불안 (Anxious)
- 당황 (Embarrassed)
- 행복 (Happy)
- 상처 (Hurt)
- 슬픔 (Sad)

### 🎮 미니게임 API
- 난이도별 문장 제공 (쉬움/보통/어려움)
- 발음 정확도 계산 (STT 기반)
- 세션 관리(메모리 + Sticky Session) 및 점수 기록 

### 💬 커뮤니티 API
- 게시글 CRUD (생성/조회/수정/삭제)
- 댓글 및 대댓글 시스템
- 좋아요(계정별 기억) 기능

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          전체 아키텍처                                   │
└─────────────────────────────────────────────────────────────────────────┘

[Frontend]
     │
     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend Server                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │   Routers    │  │   Services   │  │   Database   │                │
│  │  (Endpoints) │→ │  (비즈니스    │→ │  (SQLAlchemy)│                │
│  └──────────────┘  │   로직)       │  └──────────────┘                │
│                    └──────────────┘                                    │
└────────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌──────────────────┐   ┌────────────────┐
│  Google STT   │   │  Wav2Vec2 Model  │   │  OpenAI GPT    │
│  API          │   │  (AWS S3)        │   │  API           │
└───────────────┘   └──────────────────┘   └────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  SVM Classifier │
                    │  (Emotion)      │
                    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        CI/CD 파이프라인                                  │
└─────────────────────────────────────────────────────────────────────────┘

[GitHub Push] → [GitHub Actions]
                      │
                      ├─→ [모델 업로드: HuggingFace]
                      ├─→ [Docker 빌드 & 푸시: ECR]
                      └─→ [컨테이너 배포: ECS]
```

---

## 🛠️ 기술 스택

| 분류 | 기술                                              |
|------|-------------------------------------------------|
| **Backend Framework** | FastAPI 0.115.5, Uvicorn 0.24.0                 |
| **언어** | Python 3.10                                     |
| **Database** | SQLAlchemy 2.0.44 (ORM), MySQL (AsyncMy)        |
| **인증** | JWT, Kakao OAuth2, Bcrypt                       |
| **STT** | Google Cloud Speech-to-Text, OpenAI Whisper     |
| **NLP** | Transformers 4.57.3, BERT (KoBERT)              |
| **음성 분석** | Librosa 0.10.1, Wav2Vec2                        |
| **ML/AI** | PyTorch 2.9.1, Scikit-learn 1.3.2, NumPy 1.26.4 |
| **LLM** | OpenAI API 1.10.0                               |
| **벡터 DB** | ChromaDB 0.5.11 (RAG)                           |
| **파일 처리** | Pillow 12.0.0 (이미지), AudioRead 3.1.0            |
| **클라우드** | Boto3 1.34.156 (AWS SDK)                        |
| **DevOps** | Docker, GitHub Actions, AWS (ECS, S3, ECR)      |

---

## 📁 프로젝트 구조

```
backend/
├── app/
│   ├── core/                      # 핵심 설정
│   │   ├── settings.py            # 환경변수 관리
│   │   ├── security.py            # 비밀번호 해싱
│   │   ├── jwt.py                 # JWT 토큰 관리
│   │   ├── model_loader.py        # S3에서 모델 다운로드
│   │   └── presentation_standards.py  # 발표 평가 기준
│   ├── database/
│   │   ├── base.py                # Database 세션
│   │   ├── database.py            # Database 연결
│   │   ├── models/                # SQLAlchemy 모델
│   │   │   ├── user.py
│   │   │   ├── interview.py
│   │   │   ├── communication.py
│   │   │   ├── presentation.py
│   │   │   ├── community.py
│   │   │   └── minigame.py
│   │   ├── schemas/               # Pydantic 스키마
│   │   └── crud/                  # CRUD 로직
│   ├── routers/                   # API 엔드포인트
│   │   ├── user.py                # 회원가입/로그인
│   │   ├── interview.py           # 모의 면접 API
│   │   ├── communication.py       # 대화 분석 API
│   │   ├── presentation.py        # 발표 분석 API
│   │   ├── minigame.py            # 미니게임 API
│   │   ├── community.py           # 커뮤니티 API
│   │   ├── audio.py               # 음성 파일 관리
│   │   └── jobs.py                # 직업 카테고리
│   ├── service/                   # 비즈니스 로직
│   │   ├── stt_service.py         # Google STT
│   │   ├── whisper_stt_service.py # Whisper STT
│   │   ├── i_bert_service.py      # 면접 BERT 분석
│   │   ├── c_bert_service.py      # 대화 BERT 분석
│   │   ├── voice_analyzer.py      # Librosa 음향 분석
│   │   ├── presentation_analysis_service.py  # Wav2Vec2 감정 분석
│   │   ├── presentation_scorer.py # 점수 계산
│   │   ├── llm_service.py         # OpenAI 피드백 생성
│   │   ├── kakao_oauth.py         # 카카오 로그인
│   │   └── email_service.py       # 이메일 발송
│   ├── prompts/                   # LLM 프롬프트
│   │   ├── interview_prompts.py
│   │   ├── communication_prompts.py
│   │   └── presentation_prompts.py
│   ├── infra/
│   │   └── chroma_db.py           # 벡터 DB 연결
│   └── utils/
│       └── init_minigame_data.py  # 미니게임 초기 데이터
├── alembic/                       # Database 마이그레이션
├── .github/workflows/
│   └── deploy.yml                 # CI/CD 파이프라인
├── Dockerfile                     # Docker 이미지 빌드
├── docker-compose.yml             # 로컬 개발 환경
├── main.py                        # FastAPI 앱 진입점
├── requirements.txt               # Python 의존성
└── entrypoint.sh                  # 컨테이너 시작 스크립트
```

---

## 🚀 실행 방법

### 환경 요구사항
- Python 3.10
- MySQL 8.0 이상
- Docker (선택)
- AWS 계정 (S3 모델 학습 가중치 다운로드 용)

### 로컬 개발 환경 (Python)

```bash
# 1. 저장소 클론
git clone https://github.com/your-repo/TeamProject_Backend.git
cd TeamProject_Backend

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경변수 설정
cp .env.example .env
# .env 파일에 필요한 값 입력

# 5. 데이터베이스 마이그레이션
alembic upgrade head

# 6. 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8081

# 7. API 문서 확인
http://localhost:8081/docs
```

### Docker 환경

```bash
# 1. Docker Compose 실행
docker-compose up --build

# 2. API 접속
http://localhost:8081/docs
```

---

## 🔧 주요 기능 구현

### 1. Google STT 음성 인식

```python
from google.cloud import speech

def transcribe_audio(audio_file: bytes, language: str = "ko-KR"):
    client = speech.SpeechClient()
    
    audio = speech.RecognitionAudio(content=audio_file)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code=language,
        enable_speaker_diarization=True,  # 화자 분리
        diarization_speaker_count=2,
    )
    
    response = client.recognize(config=config, audio=audio)
    return response.results
```

### 2. BERT 부적절 표현 감지

```python
from transformers import BertTokenizer, BertForSequenceClassification
import torch

def detect_inappropriate_text(text: str):
    tokenizer = BertTokenizer.from_pretrained("monologg/kobert")
    model = BertForSequenceClassification.from_pretrained("your-model")
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = model(**inputs)
    scores = torch.softmax(outputs.logits, dim=1)
    
    return {
        "inappropriate_score": scores[0][1].item(),
        "is_inappropriate": scores[0][1].item() > 0.7
    }
```

### 3. Wav2Vec2 감정 분석

```python
import torch
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import pickle

def analyze_emotion(audio_array):
    # 1. Wav2Vec2로 음성 벡터 추출
    processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-xlsr-300m")
    model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-xlsr-300m")
    
    inputs = processor(audio_array, sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        features = model(**inputs).last_hidden_state.mean(dim=1).numpy()
    
    # 2. SVM 분류기로 감정 예측
    with open("emotion_classifier.pkl", "rb") as f:
        classifier = pickle.load(f)
    
    emotion = classifier.predict(features)[0]
    return emotion  # "happy", "sad", "angry", etc.
```

### 4. Librosa 음향 분석

```python
import librosa
import numpy as np

def analyze_voice_features(audio_file: str):
    y, sr = librosa.load(audio_file)
    
    # 말하기 속도
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    
    # 피치 추출
    pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
    pitch_values = []
    for t in range(pitches.shape[1]):
        index = magnitudes[:, t].argmax()
        pitch = pitches[index, t]
        if pitch > 0:
            pitch_values.append(pitch)
    
    return {
        "speech_rate": float(tempo),
        "pitch_mean": float(np.mean(pitch_values)),
        "pitch_std": float(np.std(pitch_values)),
        "pitch_range": float(np.max(pitch_values) - np.min(pitch_values))
    }
```

### 5. OpenAI 피드백 생성

```python
from openai import OpenAI

def generate_feedback(analysis_data: dict):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
    사용자의 발표 분석 결과:
    - 말하기 속도: {analysis_data['speech_rate']} 단어/분
    - 억양 변화: {analysis_data['pitch_std']}
    - 감정 상태: {analysis_data['emotion']}
    
    위 결과를 바탕으로 구체적이고 긍정적인 피드백을 작성해주세요.
    """
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content
```

---

## 📊 주요 API 엔드포인트

### 인증
- `POST /api/auth/signup` - 회원가입
- `POST /api/auth/login` - 로그인
- `POST /api/auth/refresh` - 토큰 갱신
- `GET /api/auth/kakao/callback` - 카카오 로그인 콜백

### 모의 면접
- `POST /api/interview/session` - 세션 생성
- `POST /api/interview/upload` - 음성 업로드 및 분석
- `GET /api/interview/result/{session_id}` - 결과 조회
- `GET /api/interview/history` - 이력 조회

### 대화 분석
- `POST /api/communication/upload` - 음성 업로드
- `POST /api/communication/speaker-select` - 화자 선택
- `POST /api/communication/analyze` - 분석 실행
- `GET /api/communication/result/{id}` - 결과 조회

### 발표 분석
- `POST /api/presentation/upload` - 음성 업로드
- `POST /api/presentation/analyze` - 분석 실행
- `GET /api/presentation/result/{id}` - 결과 조회

### 미니게임
- `GET /api/minigame/sentences` - 문장 목록
- `POST /api/minigame/submit` - 답안 제출
- `GET /api/minigame/score` - 점수 조회

### 커뮤니티
- `GET /api/community/posts` - 게시글 목록
- `POST /api/community/posts` - 게시글 작성
- `GET /api/community/posts/{id}` - 게시글 상세
- `POST /api/community/comments` - 댓글 작성

---

## 🚀 CI/CD 파이프라인

### GitHub Actions Workflow

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Upload models to S3
        run: aws s3 sync app/ml_models s3://${{ secrets.S3_MODEL_BUCKET }}/
      
      - name: Build Docker image
        run: docker build -t backend .
      
      - name: Push to ECR
        run: docker push $ECR_REGISTRY/backend:latest
      
      - name: Deploy to EC2
        run: ssh ec2-user@${{ secrets.EC2_HOST }} "docker pull && docker restart"
```

### 배포 프로세스

1. **코드 푸시** → GitHub
2. **모델 업로드** → AWS S3
3. **Docker 빌드** → ECR 푸시
4. **EC2 배포** → 컨테이너 재시작

---

## 🔒 보안

### 구현된 보안 기능
- JWT 기반 인증 (Access Token + Refresh Token)
- Bcrypt 비밀번호 해싱
- CORS 설정
- Rate Limiting (SlowAPI)
- SQL Injection 방지 (SQLAlchemy ORM)
- 환경변수 기반 민감 정보 관리

---

## ⚙️ 환경 변수 (.env)

```env
# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=steach

# JWT
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# OpenAI
OPENAI_API_KEY=sk-...

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_MODEL_BUCKET=your-bucket
AWS_REGION=ap-northeast-2

# Kakao OAuth
KAKAO_CLIENT_ID=your_client_id
KAKAO_CLIENT_SECRET=your_secret
```

---

## 📈 성능 최적화

### 구현된 최적화
- 비동기 I/O (FastAPI + SQLAlchemy Async)
- 모델 캐싱 (싱글톤 패턴)
- S3 기반 모델 관리 (메모리 효율)
- 배치 처리 (음성 파일 분할 처리)
- Connection Pooling (데이터베이스)

### 서버 사양 권장
- **개발/테스트**: EC2 t3.medium (4GB RAM)
- **프로덕션**: EC2 t3.large (8GB RAM) + Swap 2GB

---

## 🐛 트러블슈팅

### 메모리 부족 에러

**증상**: 서버가 멈추거나 OOM 에러 발생

**해결**:
```bash
# Swap 메모리 추가 (EC2)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### S3 모델 가중치 다운로드 실패

**증상**: `NoCredentialsError` 발생

**해결**:
1. EC2 IAM 역할에 S3 권한 추가
2. 환경변수 확인 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)

---

## 📝 라이선스

This project is licensed under the MIT License.

---

## 👥 팀 구성원

| 이름 | 역할 | <br>
| 이경준 | PL, Wav2Vec2, Presentation, Minigame, Authentication, Community, Infra/Deploy | <br>
| 하태호 | Interview, ChromaDB, Google STT, BERT | <br>
| 김가현 | Interview, ChromaDB, Google STT, BERT | <br>
| 손연서 | Communication, Google STT, BERT | <br>



