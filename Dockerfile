FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
ENV RUNNING_IN_DOCKER=true
WORKDIR /app

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*
  
# requirements.txt 기반 설치 (권장)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]