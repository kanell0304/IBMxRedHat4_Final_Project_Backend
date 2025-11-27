import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model = AutoModelForSequenceClassification.from_pretrained("./I_P_BERT")
tokenizer = AutoTokenizer.from_pretrained("./I_P_BERT")
device = "cpu"

def predict(sentence):
  token = tokenizer(
    [sentence],
    truncation=True,
    padding='max_length',
    max_length=64,
    return_tensors='pt'
  )

  model.eval()
  with torch.no_grad():
    logits = model(
      input_ids=token["input_ids"].to(device),
      attention_mask=token["attention_mask"].to(device)
    ).logits

  probs = torch.sigmoid(logits).cpu().numpy()[0]
  preds = (probs > 0.5).astype(int)

  return preds, probs


sent = "음 제가 생각하기에는 이런 식으로 얘기하면 좋을 것 같습니다."
pred, prob = predict(sent)

print("예측 결과:", pred)
print("확률:", prob)


# podman run --rm -it final-app /bin/bash

# 예측 결과: [0 0 0 1 0 0 1]
#확률: [0.00921554 0.10378359 0.00953329 0.99888426 0.00922274 0.00682631 0.99837875]