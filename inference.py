from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel, PeftConfig
import torch

MODEL_NAME = "taeeho/C_BERT"
label_names = ["slang", "biased", "curse", "filler"]

config = PeftConfig.from_pretrained(MODEL_NAME)

base = AutoModelForSequenceClassification.from_pretrained(
  config.base_model_name_or_path,
  num_labels=4
)

model = PeftModel.from_pretrained(base, MODEL_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def bert_prob(text: str):
  encoded = tokenizer(text, return_tensors="pt")
  output = model(**encoded)
  preds = torch.sigmoid(output.logits).detach().numpy()[0]

  results = {}
  for i, label in enumerate(label_names):
    results[label] = float(preds[i])
  return results

def bert_binary(text: str, threshold: float = 0.5):
  encoded = tokenizer(text, return_tensors="pt")
  output = model(**encoded)
  preds = torch.sigmoid(output.logits).detach().numpy()[0]

  results = {}
  for i, label in enumerate(label_names):
    results[label] = int(preds[i] >= threshold)
  return results