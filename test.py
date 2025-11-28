from inference import bert_prob, bert_binary
import json
a = bert_prob("아이씨 진짜 뭐냐")
b = bert_binary("아이씨 진짜 뭐냐")

print(json.dumps(a, ensure_ascii=False, indent=2))
print(json.dumps(b, ensure_ascii=False, indent=2))