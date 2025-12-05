import chromadb, json, pathlib
path = pathlib.Path(__file__).resolve().parent / "chroma_db"
c = chromadb.PersistentClient(path=str(path))
col = c.get_or_create_collection("interview_answers")
print("Total:", col.count())
res = col.peek(limit=5)
for i, m in zip(res["ids"], res["metadatas"]):
    print(i, json.dumps(m, ensure_ascii=False))