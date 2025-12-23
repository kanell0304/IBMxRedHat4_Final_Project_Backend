import torch
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel, PeftConfig
from typing import Optional

# 베이스 모델을 먼저 로드하고 그 다음으로 어댑터 가중치를 얹어서 추론
class InferenceService:
  def __init__(self, max_len: int = 64, local_files_only: bool = False, device_mode: str = "cpu"):
    self.model_name = "taeeho/c_bert_lora"
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
    
    self.CURSE_WORDS = ["존나", "씨발", "병신", "개새끼", "좆", "좆같"]
    # 부분 일치로도 잡을 단어들
    self.BIASED_SUBSTRING = ["장애인", "병신"]
    # 단어(어절) 단위로만 잡을 단어들 (오탐 방지: 애자일, 따뜻한 등)
    self.BIASED_EXACT = ["애자", "따"]
    self.FILLER_WORDS = ["음", "어", "어 음"]

  def tokenize(self, text: str):
    encoded = self.tokenizer(text, return_tensors="pt", truncation=True, padding="max_length", max_length=self.max_len)
    return {k: v.to(self.device) for k, v in encoded.items()}

  def rule_curse(self, sentence: str) -> bool:
    s = sentence.replace(" ", "")
    for w in self.CURSE_WORDS:
      if w in s:
        print(f"!!! 욕설 감지됨 (단어: {w}) - 원문: {sentence}")
        return True
    return False

  def rule_biased(self, sentence: str) -> bool:
    # 1. Substring check
    s = sentence.replace(" ", "")
    for w in self.BIASED_SUBSTRING:
      if w in s:
        print(f"!!! 차별/비하 감지됨 (단어: {w}) - 원문: {sentence}")
        return True
        
    # 2. Exact word check (Regex)
    regex = r'(?<!\S)(' + '|'.join(map(re.escape, self.BIASED_EXACT)) + r')(?=$|[ \.,!?]|은|는|이|가|을|를|의|도|로|고|만|에)'
    
    match = re.search(regex, sentence)
    if match:
        print(f"!!! 차별/비하 감지됨 (단어: {match.group()}) - 원문: {sentence}")
        return True
    return False

  def rule_filler(self, sentence: str) -> bool:
    # Use regex to match fillers as standalone words
    regex = r'(?<!\S)(?:' + '|'.join(map(re.escape, self.FILLER_WORDS)) + r')(?!\S)'
    if re.search(regex, sentence):
      print(f"!!! 추임새 감지됨 - 원문: {sentence}")
      return True
    return False

  def predict_probs(self, text: str):
    encoded = self.tokenize(text)
    with torch.no_grad():
      outputs = self.model(**encoded)
      probs = torch.sigmoid(outputs.logits[0]).cpu().numpy()
    
    result = {label: float(p) for label, p in zip(self.labels, probs)}
    
    # 룰 기반 강제 적용 (오탐 방지)
    
    # 1. 욕설/비속어 (Curse & Slang)
    if self.rule_curse(text):
      result["curse"] = 1.0
      result["slang"] = 0.0 # curse 라벨로 통합 관리
    else:
      result["curse"] = 0.0
      result["slang"] = 0.0

    # 2. 차별/비하 (Biased)
    if self.rule_biased(text):
      result["biased"] = 1.0
    else:
      result["biased"] = 0.0
      
    # 3. 필러 (Filler)
    if self.rule_filler(text):
      result["filler"] = 1.0
      
    return result

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