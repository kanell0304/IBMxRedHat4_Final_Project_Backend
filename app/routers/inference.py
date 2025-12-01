from fastapi import APIRouter
from app.service.c_inference_service import get_inference_service as get_c
from app.service.i_inference_service import get_inference_service as get_i

router = APIRouter(prefix="/bert", tags=["bert"])

@router.post("/c")
def c(text: str):
  svc = get_c()
  return svc.predict_labels(text)

@router.post("/i")
def i(text: str):
  svc = get_i()
  return svc.predict_labels(text)