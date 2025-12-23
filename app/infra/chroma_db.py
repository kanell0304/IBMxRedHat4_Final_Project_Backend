import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

# client
persist_dir = Path(__file__).resolve().parents[2] / "chroma_db"
persist_dir.mkdir(parents=True, exist_ok=True)
client = chromadb.PersistentClient(path=str(persist_dir))

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