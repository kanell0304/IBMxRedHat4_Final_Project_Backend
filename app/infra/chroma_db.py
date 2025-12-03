import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# chroma client 생성
client = chromadb.Client(
  Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="chroma_db"  # 저장 경로
  )
)

# Collection 생성/가져오기
collection = client.get_or_create_collection(
  name="interview_answers",
  metadata={"hnsw:space": "cosine"}  # 거리 측정 방식
)

# 임베딩 모델 한 번만 로드
embed_model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# 임베딩 함수
def get_embedding(text: str):
  vec = embed_model.encode([text])[0]
  return vec.tolist()