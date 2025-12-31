# AWS CI/CD 배포 가이드

## 프로젝트 개요

### 아키텍처
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          전체 아키텍처                                   │
└─────────────────────────────────────────────────────────────────────────┘

[사용자] ──→ [CloudFront] ──→ [S3: Frontend]
                │
                └──→ [EC2: Backend] ←── [S3: ML Models]
                            │
                            └──→ [RDS: Database] (선택)

┌─────────────────────────────────────────────────────────────────────────┐
│                        CI/CD 파이프라인                                  │
└─────────────────────────────────────────────────────────────────────────┘

[GitHub Push] → [GitHub Actions] → [ECR] → [EC2]
                      │
                      └──→ [S3: Model Upload]
```

### 기술 스택
| 구분 | 기술 |
|------|------|
| Frontend | React + CloudFront + S3 |
| Backend | FastAPI + EC2 + Docker |
| ML Model | Wav2Vec2 (특징 추출) + sklearn SVM (감정 분류) |
| Model Storage | AWS S3 |
| Container Registry | AWS ECR |
| CI/CD | GitHub Actions |

---

## 목차

1. [Backend 배포](#backend-배포)
   - [Step 1: S3 버킷 생성](#step-1-s3-버킷-생성)
   - [Step 2: 모델 파일 업로드](#step-2-모델-파일-s3-업로드)
   - [Step 3: 코드 수정](#step-3-코드-수정)
   - [Step 4: ECR 리포지토리 생성](#step-4-ecr-리포지토리-생성)
   - [Step 5: EC2 인스턴스 생성](#step-5-ec2-인스턴스-생성)
   - [Step 6: IAM 역할 설정](#step-6-iam-역할-설정)
   - [Step 7: EC2 초기 설정](#step-7-ec2-초기-설정)
   - [Step 8: GitHub Secrets 설정](#step-8-github-secrets-설정)
   - [Step 9: CI/CD 배포 테스트](#step-9-cicd-배포-테스트)
2. [Frontend 배포](#frontend-배포)
3. [발생한 문제 및 해결](#발생한-문제-및-해결)
4. [중요 주의사항](#중요-주의사항)
5. [비용 정보](#비용-정보)

---

# Backend 배포

## Step 1: S3 버킷 생성

ML 모델 파일(`.pkl`)을 저장할 S3 버킷 생성

### 생성 방법
1. [AWS S3 콘솔](https://s3.console.aws.amazon.com/) 접속
2. **버킷 만들기** 클릭
3. 설정:
   - 버킷 이름: `team2-backend-wav2vec-pkl` (전 세계 고유해야 함)
   - 리전: `아시아 태평양(서울) ap-northeast-2`
   - 퍼블릭 액세스 차단: **모두 체크**
4. **버킷 만들기** 클릭

### 결과
```
버킷 이름: team2-backend-wav2vec-pkl
리전: ap-northeast-2
```

---

## Step 2: 모델 파일 S3 업로드

### 업로드 파일 목록
| 파일명 | 용량 | 설명 |
|--------|------|------|
| `emotion_classifier.pkl` | ~59MB | SVM 감정 분류 모델 |
| `scaler.pkl` | ~0.1MB | StandardScaler |
| `label_mapping.pkl` | ~0.1MB | 감정 레이블 매핑 |

### 업로드 방법

#### 방법 1: AWS 콘솔
1. S3 버킷 접속
2. **업로드** 클릭
3. 3개 파일 드래그 앤 드롭
4. **업로드** 클릭

#### 방법 2: AWS CLI
```bash
aws s3 cp app/ml_models/emotion_classifier.pkl s3://team2-backend-wav2vec-pkl/
aws s3 cp app/ml_models/scaler.pkl s3://team2-backend-wav2vec-pkl/
aws s3 cp app/ml_models/label_mapping.pkl s3://team2-backend-wav2vec-pkl/

# 확인
aws s3 ls s3://team2-backend-wav2vec-pkl/
```

### 중요: 업로드 경로
모델 파일을 **버킷 루트**에 직접 업로드했으므로 `S3_MODEL_PREFIX`는 빈 값으로 설정

```
s3://team2-backend-wav2vec-pkl/emotion_classifier.pkl  (루트)
s3://team2-backend-wav2vec-pkl/models/emotion_classifier.pkl  (폴더 안)
```

---

## Step 3: 코드 수정

### 3-1. `.gitignore` 수정

모델 파일이 Git에 올라가지 않도록 설정:

```gitignore
# ML Models (S3에서 관리)
app/ml_models/*.pkl
!app/ml_models/__init__.py
```

### 3-2. `requirements.txt`에 boto3 추가

```txt
boto3>=1.28.0
```

### 3-3. `app/core/model_loader.py` 생성

S3에서 모델을 다운로드하는 로직:

```python
import boto3
import os
from pathlib import Path
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError

# .env 파일 로드
load_dotenv()

# 모델 파일 경로
MODEL_DIR = Path(__file__).parent.parent / "ml_models"

# S3 설정
S3_BUCKET = os.getenv("S3_MODEL_BUCKET", "")
S3_MODEL_PREFIX = os.getenv("S3_MODEL_PREFIX", "")

# 관리할 모델 파일 목록
MODEL_FILES = [
    "emotion_classifier.pkl",
    "scaler.pkl",
    "label_mapping.pkl"
]


def is_s3_enabled() -> bool:
    return bool(S3_BUCKET)


def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "ap-northeast-2")
    )


def check_local_models() -> dict:
    status = {}
    for model_name in MODEL_FILES:
        local_path = MODEL_DIR / model_name
        status[model_name] = local_path.exists()
    return status


def download_model_from_s3(model_name: str, force: bool = False) -> bool:
    local_path = MODEL_DIR / model_name
    s3_key = f"{S3_MODEL_PREFIX}{model_name}"

    if local_path.exists() and not force:
        print(f"  {model_name} 이미 존재 (스킵)")
        return True

    try:
        s3 = get_s3_client()
        print(f"  {model_name} S3에서 다운로드 중...")

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        s3.download_file(S3_BUCKET, s3_key, str(local_path))

        size_mb = local_path.stat().st_size / (1024 * 1024)
        print(f"  {model_name} 완료 ({size_mb:.1f} MB)")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"  {model_name} S3에 없음")
        else:
            print(f"  {model_name} 다운로드 실패: {e}")
        return False
    except NoCredentialsError:
        print(f"  AWS 자격 증명 없음")
        return False
    except Exception as e:
        print(f"  {model_name} 오류: {e}")
        return False


def download_all_models_from_s3(force: bool = False) -> bool:
    print(f"  버킷: {S3_BUCKET}")
    print(f"  경로: {S3_MODEL_PREFIX}")

    success_count = 0
    for model_name in MODEL_FILES:
        if download_model_from_s3(model_name, force):
            success_count += 1

    return success_count == len(MODEL_FILES)


def ensure_models_ready() -> bool:
    """모델 파일 준비 (로컬 우선, 없으면 S3)"""
    print("모델 파일 확인 중...")

    # 로컬 파일 확인
    local_status = check_local_models()
    all_local = all(local_status.values())
    missing = [name for name, exists in local_status.items() if not exists]

    if all_local:
        print("모든 모델 파일이 로컬에 존재합니다.")
        for name in MODEL_FILES:
            size_mb = (MODEL_DIR / name).stat().st_size / (1024 * 1024)
            print(f"  {name} ({size_mb:.1f} MB)")
        return True

    # 로컬에 없는 파일이 있음
    print(f"누락된 파일: {missing}")

    # S3 설정 확인
    if not is_s3_enabled():
        print("")
        print("S3 설정이 없습니다.")
        print("   로컬 파일을 직접 배치하거나 .env에 S3 설정을 추가하세요:")
        print("   - S3_MODEL_BUCKET=your-bucket-name")
        print("   - AWS_ACCESS_KEY_ID=your-key")
        print("   - AWS_SECRET_ACCESS_KEY=your-secret")
        return False

    # S3에서 다운로드
    print("")
    print("S3에서 다운로드 시도...")
    success = download_all_models_from_s3()

    if success:
        print("")
        print("모든 모델 다운로드 완료!")
    else:
        print("")
        print("일부 모델 다운로드 실패")

    return success
```

### 3-4. `main.py` 수정

서버 시작 시 모델 파일 확인 로직 추가:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import voice_analysis
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n서버 시작")

    # 1. 모델 파일 확인 (로컬 우선, 없으면 S3)
    try:
        from app.core.model_loader import ensure_models_ready
        models_ready = ensure_models_ready()

        if not models_ready:
            print("일부 모델 파일이 없습니다. 일부 기능이 제한될 수 있습니다.")
    except Exception as e:
        print(f"모델 파일 확인 실패: {e}")

    # 2. 음성 분석기 로드
    try:
        from app.service.voice_analyzer import get_analyzer
        analyzer = get_analyzer()
        print("음성 분석 모델 로드 완료")
    except Exception as e:
        print(f"모델 로드 실패: {e}")

    print("")
    yield
    print("\n서버 종료")


app = FastAPI(
    title="Team Project API",
    description="음성 분석 API",
    version="1.0.0",
    lifespan=lifespan
)

# ... 나머지 코드
```

### 3-5. `.env` 파일 설정

```env
# AWS S3 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-northeast-2
S3_MODEL_BUCKET=team2-backend-wav2vec-pkl
S3_MODEL_PREFIX=
```

### 3-6. `Dockerfile` 수정

```dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# requirements.txt 기반 설치 (boto3 포함)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]
```

### 3-7. `.github/workflows/deploy.yml` 생성

```yaml
name: Deploy to AWS

on:
  push:
    branches: [develop_presentation]  # 배포할 브랜치
  workflow_dispatch:  # 수동 실행 가능

env:
  AWS_REGION: ap-northeast-2
  ECR_REPOSITORY: teamproject-backend

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      # 1. 코드 체크아웃
      - name: Checkout code
        uses: actions/checkout@v4

      # 2. AWS 자격 증명 설정
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      # 3. 모델 파일이 있으면 S3에 업로드
      - name: Upload models to S3
        run: |
          echo "모델 파일 S3 업로드 확인 중..."
          
          if [ -d "app/ml_models" ]; then
            for file in app/ml_models/*.pkl; do
              if [ -f "$file" ]; then
                filename=$(basename "$file")
                echo "  업로드: $filename"
                aws s3 cp "$file" "s3://${{ secrets.S3_MODEL_BUCKET }}/$filename"
              fi
            done
            echo "S3 업로드 완료"
          else
            echo "ml_models 폴더 없음 (스킵)"
          fi

      # 4. ECR 로그인
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      # 5. Docker 이미지 빌드 & 푸시
      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          echo "Docker 이미지 빌드 중..."
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          
          echo "ECR에 푸시 중..."
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          
          echo "Docker 이미지 푸시 완료"

      # 6. EC2에 배포
      - name: Deploy to EC2
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USER }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            echo "EC2 배포 시작..."
            
            # 환경 변수 설정
            export AWS_REGION=ap-northeast-2
            export ECR_REGISTRY=484907489661.dkr.ecr.ap-northeast-2.amazonaws.com
            export ECR_REPOSITORY=teamproject-backend
            export S3_MODEL_BUCKET=${{ secrets.S3_MODEL_BUCKET }}
            
            # ECR 로그인
            aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
            
            # 기존 컨테이너 중지 및 삭제
            docker stop teamproject-backend 2>/dev/null || true
            docker rm teamproject-backend 2>/dev/null || true
            
            # 오래된 이미지 정리
            docker image prune -af
            
            # 새 이미지 풀
            docker pull $ECR_REGISTRY/$ECR_REPOSITORY:latest
            
            # 컨테이너 실행
            docker run -d \
              --name teamproject-backend \
              --restart unless-stopped \
              -p 8081:8081 \
              -e S3_MODEL_BUCKET=$S3_MODEL_BUCKET \
              -e S3_MODEL_PREFIX= \
              -e AWS_REGION=$AWS_REGION \
              $ECR_REGISTRY/$ECR_REPOSITORY:latest
            
            # 상태 확인
            sleep 10
            docker ps
            
            echo "배포 완료!"
```

---

## Step 4: ECR 리포지토리 생성

Docker 이미지를 저장할 ECR 리포지토리 생성

### 생성 방법
1. [ECR 콘솔](https://ap-northeast-2.console.aws.amazon.com/ecr/) 접속
2. **리포지토리 생성** 클릭
3. 설정:
   - 가시성: **프라이빗**
   - 리포지토리 이름: `teamproject-backend`
4. **생성** 클릭

### 결과
```
URI: 484907489661.dkr.ecr.ap-northeast-2.amazonaws.com/teamproject-backend
```

---

## Step 5: EC2 인스턴스 생성

### 생성 방법
1. [EC2 콘솔](https://ap-northeast-2.console.aws.amazon.com/ec2/) 접속
2. **인스턴스 시작** 클릭
3. 설정:

| 항목 | 설정값 |
|------|--------|
| 이름 | `teamproject-backend-server` |
| AMI | Amazon Linux 2023 |
| 인스턴스 유형 | `t3.medium` (4GB RAM) |
| 키 페어 | 새로 생성 → `.pem` 파일 다운로드 |
| 스토리지 | 20GB 이상 |

### 보안 그룹 설정

| 유형 | 포트 | 소스 |
|------|------|------|
| SSH | 22 | 0.0.0.0/0 |
| 사용자 지정 TCP | 8081 | 0.0.0.0/0 |

> **보안 주의**: SSH를 `0.0.0.0/0`으로 열어야 GitHub Actions에서 접근 가능. 프로덕션에서는 더 제한적인 설정 권장.

### 인스턴스 유형 선택 (중요!)

| 유형 | RAM | Wav2Vec2 + 추론 | 권장 |
|------|-----|-----------------|------|
| t3.small | 2GB | 메모리 부족 | |
| t3.medium | 4GB | Swap 필요 | 개발/테스트 |
| t3.large | 8GB | 충분 | 프로덕션 |

---

## Step 6: IAM 역할 설정

EC2가 S3와 ECR에 접근할 수 있도록 IAM 역할 생성

### 중요: EC2용 역할 생성

1. [IAM 역할 생성](https://console.aws.amazon.com/iam/home#/roles$new?step=type) 접속
2. **신뢰할 수 있는 엔터티**: **AWS 서비스** → **EC2** 선택 반드시 EC2!
3. **권한 정책** 추가:
   - `AmazonS3FullAccess`
   - `AmazonEC2ContainerRegistryFullAccess`
4. 역할 이름: `EC2-Backend-Role`
5. **역할 생성**

### EC2에 역할 연결

1. EC2 콘솔 → 인스턴스 선택
2. **작업** → **보안** → **IAM 역할 수정**
3. 생성한 역할 선택 → **업데이트**

### 확인 방법 (EC2에서)
```bash
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
# 역할 이름이 출력되면 성공
```

---

## Step 7: EC2 초기 설정

### SSH 접속 (MobaXterm 권장)

1. MobaXterm 실행
2. **Session** → **SSH**
3. 설정:
   - Host: `{EC2 퍼블릭 IP}`
   - Username: `ec2-user`
   - Private key: `.pem` 파일 선택
4. **OK**

### Docker 설치

```bash
# 패키지 업데이트
sudo yum update -y

# Docker 설치
sudo yum install -y docker

# Docker 시작 & 자동 시작 설정
sudo systemctl start docker
sudo systemctl enable docker

# ec2-user가 docker 사용 가능하도록
sudo usermod -aG docker ec2-user

# 재접속 필요!
exit
```

### 재접속 후 확인

```bash
# Docker 확인
docker --version

# ECR 로그인 테스트
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin 484907489661.dkr.ecr.ap-northeast-2.amazonaws.com
# "Login Succeeded" 출력되면 성공
```

### Swap 메모리 추가 (t3.medium 사용 시 권장)

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 확인
free -h
# Swap: 2.0Gi 표시되면 성공
```

---

## Step 8: GitHub Secrets 설정

GitHub 리포지토리 → **Settings** → **Secrets and variables** → **Actions**

| Secret Name | Value | 설명 |
|-------------|-------|------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | IAM 사용자 Access Key |
| `AWS_SECRET_ACCESS_KEY` | `Zm1A...` | IAM 사용자 Secret Key |
| `S3_MODEL_BUCKET` | `team2-backend-wav2vec-pkl` | S3 버킷 이름 |
| `EC2_HOST` | `13.125.203.199` | EC2 퍼블릭 IP |
| `EC2_USER` | `ec2-user` | SSH 사용자명 |
| `EC2_SSH_KEY` | `-----BEGIN RSA...` | .pem 파일 전체 내용 |

---

## Step 9: CI/CD 배포 테스트

### 배포 실행

```bash
git add .
git commit -m "feat: AWS S3 + CI/CD 설정"
git push origin develop_presentation
```

### 배포 확인

1. GitHub → **Actions** 탭
2. 워크플로우 실행 확인
3. 소요 시간: 약 7~10분

### API 테스트

```bash
# EC2에서
curl http://localhost:8081/health

# 브라우저에서
http://{EC2_IP}:8081/health
http://{EC2_IP}:8081/docs
```

---

# Frontend 배포

> Frontend는 CloudFront + S3로 배포 (별도 가이드)

### 주의사항

Frontend에서 Backend API 주소 설정 필요:

```javascript
// .env 또는 config 파일
REACT_APP_API_URL=http://{EC2_IP}:8081
// 또는
VITE_API_URL=http://{EC2_IP}:8081
```

EC2 IP가 변경되면 Frontend도 업데이트 필요!

---

# 발생한 문제 및 해결

## 1. SSH 연결 타임아웃

### 증상
```
dial tcp ***:22: i/o timeout
```

### 원인
EC2 보안 그룹에서 SSH(22)가 "내 IP"만 허용

### 해결
보안 그룹 인바운드 규칙에서 SSH(22)를 `0.0.0.0/0`으로 변경

---

## 2. 메모리 부족 (서버 멈춤)

### 증상
- EC2 SSH 접속 불가
- MobaXterm에서 입력 안 됨
- EC2 Instance Connect도 연결 안 됨

### 원인
- t3.small (2GB)에서 Wav2Vec2 (~1.2GB) 로드 시 메모리 부족
- 컨테이너 무한 재시작 루프

### 해결
1. EC2 콘솔에서 **인스턴스 재부팅** 또는 **중지 → 시작**
2. **인스턴스 유형 변경**: t3.small → t3.medium (4GB)
3. **Swap 메모리 추가** (2GB)

---

## 3. IAM 역할 연결 안 됨

### 증상
```bash
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
# 아무것도 출력 안 됨
```

### 원인
IAM 역할 생성 시 신뢰 정책에 EC2가 설정되지 않음

### 해결
역할 생성 시 **신뢰할 수 있는 엔터티**에서 반드시 **EC2** 선택

---

## 4. .env 파일 로드 안 됨

### 증상
```
S3 설정이 없습니다.
```
(.env에 설정했는데도 인식 못함)

### 원인
`model_loader.py`에서 dotenv 로드 안 함

### 해결
```python
from dotenv import load_dotenv
load_dotenv()  # 파일 상단에 추가
```

---

## 5. EC2 IP 변경

### 증상
인스턴스 중지 → 시작 후 IP가 바뀜

### 영향
- GitHub Secret `EC2_HOST` 업데이트 필요
- Frontend API 주소 업데이트 필요

### 해결 (선택)
**Elastic IP** 할당하면 IP 고정 가능 (사용 중일 때 무료)

---

# 중요 주의사항

## 보안

1. **AWS 키 노출 금지**: `.env` 파일은 `.gitignore`에 추가
2. **SSH 포트**: 프로덕션에서는 특정 IP만 허용 권장
3. **.pem 파일**: 안전하게 보관, Git에 업로드 금지

## 메모리

| 모델 | 메모리 |
|------|--------|
| Wav2Vec2 XLSR_300M | ~1.2GB |
| sklearn 분류기 | ~0.1GB |
| FastAPI + 라이브러리 | ~0.3GB |
| **최소 필요** | **4GB 이상** |

## IP 변경

EC2 인스턴스 **중지 → 시작** 시 퍼블릭 IP 변경됨!
- GitHub Secret `EC2_HOST` 업데이트
- Frontend API 주소 업데이트

## 배포 브랜치

`deploy.yml`에서 배포할 브랜치 확인:
```yaml
on:
  push:
    branches: [develop_presentation]  # 이 브랜치에 푸시해야 배포됨
```

---

# 비용 정보

## EC2 인스턴스 (서울 리전).

| 유형 | 시간당 | 하루 (24h) | 월 (720h) |
|------|--------|-----------|-----------|
| t3.small | $0.026 | $0.62 | ~$19 |
| t3.medium | $0.052 | $1.25 | ~$38 |
| t3.large | $0.104 | $2.50 | ~$76 |

## 비용 절약 팁

1. **사용하지 않을 때 인스턴스 중지**
2. 발표/데모 때만 t3.large 사용
3. Swap 메모리로 t3.medium 활용

## 기타 서비스

| 서비스 | 예상 비용 |
|--------|----------|
| S3 (62MB) | ~$0.01/월 |
| ECR | ~$0.10/월 |
| 데이터 전송 | 사용량에 따라 |

---

# 체크리스트

## Backend 배포

- [ ] S3 버킷 생성
- [ ] 모델 파일 S3 업로드
- [ ] 코드 수정 (model_loader.py, main.py, .env, Dockerfile)
- [ ] ECR 리포지토리 생성
- [ ] EC2 인스턴스 생성 (t3.medium 이상)
- [ ] IAM 역할 생성 & EC2에 연결
- [ ] EC2 Docker 설치
- [ ] EC2 Swap 메모리 추가
- [ ] GitHub Secrets 설정
- [ ] CI/CD 배포 테스트
- [ ] API 동작 확인

## IP 변경 시

- [ ] GitHub Secret `EC2_HOST` 업데이트
- [ ] Frontend API 주소 업데이트
