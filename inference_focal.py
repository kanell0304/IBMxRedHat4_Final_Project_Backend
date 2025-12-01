import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict


MODEL_NAME="mongnoo/I_P_BERT_merged"

LABEL_NAMES=[
    "slang",
    "biased",
    "curse",
    "filler",
    "formality inconsistency",
    "disfluency/repetition",
    "vague",
]

DEVICE="cuda" if torch.cuda.is_available() else "cpu"


def load_model_n_tokenizer():

    model=AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.to(DEVICE)
    model.eval()

    tokenizer=AutoTokenizer.from_pretrained(MODEL_NAME)

    return model, tokenizer


MODEL, TOKENIZER=load_model_n_tokenizer()


def predict_labels(
        text:str,
        threshold:float=0.45,
        max_length:int=64,
)->Dict[str, Dict[str,float]]:
    
    encoded=TOKENIZER(
        text,
        truncation=True,
        padding="max_length",
        max_length=max_length,
        return_tensors="pt",
    )

    encoded={k:v.to(DEVICE) for k, v in encoded.items()}

    with torch.no_grad():
        outputs=MODEL(**encoded)
        logits=outputs.logits[0]
        probs=torch.sigmoid(logits).cpu().numpy()

    result:Dict[str, Dict[str, float]]={}

    for label, p in zip(LABEL_NAMES, probs):
        result[label]={
            "score": float(p),
            "label": int(p>=threshold),
        }

    return result


if __name__=="__main__":
    while True:
        text = input("문장 입력 (종료하려면 빈 줄 엔터): ").strip()
        if not text:
            break

        outputs = predict_labels(text)
        print("\n=== 예측 결과 ===")
        for k, v in outputs.items():
            print(f"{k:25s} -> label={v['label']}  score={v['score']:.4f}")
        print()