FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    ffmpeg \
  && rm -rf /var/lib/apt/lists/*
  
RUN pip install --no-cache-dir \
  python-dotenv \
  sqlalchemy \
  pydantic-settings \
  pydantic \
  fastapi==0.104.1 \
  uvicorn[standard]==0.24.0 \
  python-multipart==0.0.6 \
  librosa==0.10.1 \
  numpy==1.24.3 \
  scikit-learn==1.3.2 \
  transformers==4.39.3 \
  torch==2.1.0 \
  aiofiles==23.2.1 \
  google-cloud-speech==2.26.0 \
  alembic==1.13.1 \
  asyncmy==0.2.9 \
  pymysql==1.1.0 \
  pydub==0.25.1

COPY . .
EXPOSE 8081
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081", "--workers", "2"]
