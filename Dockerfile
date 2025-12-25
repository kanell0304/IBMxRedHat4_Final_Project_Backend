FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# 시스템 패키지 설치 (curl, unzip 추가)
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
    curl \
    unzip \
  && rm -rf /var/lib/apt/lists/*

# AWS CLI 설치 (S3에서 Google credentials 다운로드용)
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
  && unzip awscliv2.zip \
  && ./aws/install \
  && rm -rf awscliv2.zip aws

# requirements.txt 기반 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# entrypoint.sh 복사 및 실행 권한 설정
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8081

# CMD를 ENTRYPOINT로 변경
ENTRYPOINT ["/app/entrypoint.sh"]