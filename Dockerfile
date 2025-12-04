# 베이스 이미지
FROM python:3.10-slim

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV RUNNING_IN_DOCKER=true

# 작업 디렉터리 설정
WORKDIR /app

# 시스템 패키지 설치: build-essential, libsndfile1 (음성 파일 처리), ffmpeg
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# 추가된 부분: 모델 저장 디렉터리 생성 및 쓰기 권한 부여
# 1. /app/ml_models 디렉터리 생성
RUN mkdir -p /app/ml_models

# 2. 모든 사용자에게 쓰기 권한 부여 (모델 다운로드를 위함)
# 이로써 모델 로더가 파일을 저장할 때 'Permission Denied' 오류를 피할 수 있습니다.
RUN chmod -R 777 /app/ml_models
# 끝

# requirements.txt 기반 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 프로젝트 파일 복사
COPY . .

# 포트 노출 및 애플리케이션 실행 명령어
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]


# 수정 전 코드
#FROM python:3.10-slim
#
#ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
#ENV RUNNING_IN_DOCKER=true
#WORKDIR /app
#
#RUN apt-get update && \
#  apt-get install -y --no-install-recommends \
#    build-essential \
#    libsndfile1 \
#    ffmpeg \
#  && rm -rf /var/lib/apt/lists/*
#
## requirements.txt 기반 설치 (권장)1
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
#
#COPY . .
#EXPOSE 8081
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]