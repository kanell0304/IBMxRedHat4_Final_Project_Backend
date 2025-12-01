from fastapi import APIRouter
from app.service.c_inference_service import get_inference_service as get_c
from app.service.i_inference_service import get_inference_service as get_i

router = APIRouter()

@router.post("/infer/c")
def infer_c(text: str):
  svc = get_c()
  return svc.predict_labels(text)

@router.post("/infer/i")
def infer_i(text: str):
  svc = get_i()
  return svc.predict_labels(text)