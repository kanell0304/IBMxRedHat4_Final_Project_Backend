import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel
from typing import Optional, Dict

LABEL_COLS = ["slang", "biased", "curse", "filler", "formality_inconsistency", "disfluency_repetition", "vague", "ending_da"]

LABEL_THRESHOLDS: Dict[str, float] = {
  "slang": 0.70,
  "biased": 0.50,
  "curse": 0.70,
  "filler": 0.55,
  "formality_inconsistency": 0.68,
  "disfluency_repetition": 0.72,
  "vague": 0.65,
  "ending_da": 0.60,
}


class InferenceService:
  def __init__(self, max_len: int = 128, threshold: float = 0.5, local_files_only: bool = False, device_mode: str = "auto"):
    self.model_name = "taeeho/i_bert_lora"
    self.base_model_name = "bert-base-multilingual-cased"
    self.labels = LABEL_COLS
    self.label_thresholds = LABEL_THRESHOLDS
    self.max_len = max_len
    self.global_threshold = threshold
    self.device = torch.device("cuda" if device_mode == "auto" and torch.cuda.is_available() else "cpu")

    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=local_files_only)

    # base BERT
    base_model = AutoModelForSequenceClassification.from_pretrained(
      self.base_model_name,
      num_labels=len(self.labels),
      problem_type="multi_label_classification",
      local_files_only=local_files_only,
    )

    # LoRA 어댑터 로드
    self.model = PeftModel.from_pretrained(
      base_model,
      self.model_name,
      local_files_only=local_files_only,
    )
    self.model.to(self.device)
    self.model.eval()


  def tokenize(self, text: str):
    encoded = self.tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=self.max_len)
    return {k: v.to(self.device) for k, v in encoded.items()}


  def predict_probs(self, text: str) -> Dict[str, float]:
    encoded = self.tokenize(text)
    with torch.no_grad():
      outputs = self.model(**encoded)
      logits = outputs.logits[0]
      probs = torch.sigmoid(logits).cpu().numpy()
    return {label: float(p) for label, p in zip(self.labels, probs)}

  def predict_labels(self, text: str, threshold: Optional[float] = None):
    probs = self.predict_probs(text)
    use_global_th = threshold if threshold is not None else None
    results = {}
    for label in self.labels:
      p = probs[label]
      if use_global_th is not None:
        th = use_global_th
      else:
        th = self.label_thresholds.get(label, self.global_threshold)
      results[label] = {
        "score": p,
        "label": int(p >= th),
      }
    return results


# 싱글턴으로 한 번만 모델을 로드하고 이후로는 같은 인스턴스를 재사용하기 위한 헬퍼
focal_inference_service: Optional[InferenceService] = None

def get_inference_service() -> InferenceService:
  global focal_inference_service
  if focal_inference_service is None:
    focal_inference_service = InferenceService()
  return focal_inference_service