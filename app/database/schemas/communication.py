from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 대화분석 파트 스키마

class VoiceFileUpload(BaseModel):
    filename: str
    original_format: str


class VoiceFileResponse(BaseModel):
    c_vf_id: int
    c_id: int
    filename: str
    original_format: str
    duration: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class STTResultResponse(BaseModel):
    c_sr_id: int
    c_id: int
    c_vf_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CommunicationResponse(BaseModel):
    c_id: int
    user_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True