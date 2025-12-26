FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 불필요한 캐시 정리
RUN find /usr/local/lib/python3.10 -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
  && find /usr/local/lib/python3.10 -type f -name "*.pyc" -delete \
  && find /usr/local/lib/python3.10 -type f -name "*.pyo" -delete

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# 런타임 필수 패키지만 설치
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    curl \
    unzip \
  && rm -rf /var/lib/apt/lists/*

# AWS CLI 설치
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
  && unzip awscliv2.zip \
  && ./aws/install \
  && rm -rf awscliv2.zip aws

# 이전에 설치한 Python 패키지 복사
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 애플리케이션 코드 복사
COPY . .

# entrypoint.sh 복사 및 실행 권한 설정
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8081

ENTRYPOINT ["/app/entrypoint.sh"]