import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Optional

# 베이스, 어댑터가 합쳐진 하나의 모델 파일을 바로 로드
class InferenceService:
  def __init__(self, max_len: int = 64, threshold: float = 0.45, local_files_only: bool = False, device_mode: str = "cpu"):
    self.model_name = "mongnoo/I_P_BERT_merged"
    self.labels = ["slang", "biased", "curse", "filler", "formality inconsistency", "disfluency/repetition", "vague"]
    self.max_len = max_len
    self.threshold = threshold
    self.device = torch.device("cuda" if device_mode == "auto" and torch.cuda.is_available() else "cpu")

    self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name, local_files_only=local_files_only)
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

  def predict_labels(self, text: str, threshold: Optional[float] = None):
    use_th = threshold if threshold is not None else self.threshold
    probs = self.predict_probs(text)
    return {label: {"score": p, "label": int(p >= use_th)} for label, p in probs.items()}


# 싱글턴으로 모델을 한번만 로드하고 재사용
focal_inference_service: Optional[InferenceService] = None

def get_inference_service():
  global focal_inference_service
  if focal_inference_service is None:
    focal_inference_service = InferenceService()
  return focal_inference_service