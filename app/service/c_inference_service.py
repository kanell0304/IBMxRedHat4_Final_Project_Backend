import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel, PeftConfig
from typing import Dict, Optional

# 베이스 모델을 먼저 로드하고 그 다음으로 어댑터 가중치를 얹어서 추론
class InferenceService:
  def __init__(self, max_len: int = 64, local_files_only: bool = False, device_mode: str = "cpu"):
    self.model_name = "taeeho/C_BERT"
    self.labels = ["slang", "biased", "curse", "filler"]
    self.max_len = max_len
    self.device = torch.device("cuda" if device_mode == "auto" and torch.cuda.is_available() else "cpu")

    config = PeftConfig.from_pretrained(self.model_name, local_files_only=local_files_only)

    base = AutoModelForSequenceClassification.from_pretrained(
      config.base_model_name_or_path,
      num_labels=len(self.labels),
      local_files_only=local_files_only,
    )
    base.config.id2label = {i: label for i, label in enumerate(self.labels)}
    base.config.label2id = {label: i for i, label in enumerate(self.labels)}
    base.config.problem_type = "multi_label_classification"

    self.model = PeftModel.from_pretrained(base, self.model_name, local_files_only=local_files_only)
    self.model.to(self.device)
    self.model.eval()
    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=local_files_only)

  def tokenize(self, text: str):
    encoded = self.tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=self.max_len)
    return {k: v.to(self.device) for k, v in encoded.items()}

  def predict_probs(self, text: str):
    encoded = self.tokenize(text)
    with torch.no_grad():
      outputs = self.model(**encoded)
      probs = torch.sigmoid(outputs.logits[0]).cpu().numpy()
    return {label: float(p) for label, p in zip(self.labels, probs)}

  def predict_labels(self, text: str, threshold: float = 0.5):
    probs = self.predict_probs(text)
    return {label: int(score >= threshold) for label, score in probs.items()}


# 싱글턴으로 모델을 한번만 로드하고 재사용
inference_service: Optional[InferenceService] = None

def get_inference_service():
  global inference_service
  if inference_service is None:
    inference_service = InferenceService()
  return inference_service