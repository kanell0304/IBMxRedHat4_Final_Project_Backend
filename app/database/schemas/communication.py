from pydantic import BaseModel
from typing import Optional, List
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
    json_data: dict
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


class BERTResultResponse(BaseModel):
    c_br_id: int
    c_id: int
    c_sr_id: int
    target_speaker: str
    curse: int
    filler: int
    biased: int
    slang: int
    standard_score: float = 0.0
    analyzed_segments: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class CScriptSentenceResponse(BaseModel):
    c_ss_id: int
    c_id: int
    c_sr_id: int
    sentence_index: int
    speaker_label: str
    text: str
    start_time: Optional[str]
    end_time: Optional[str]
    feedback: Optional[List[dict]]
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisResultResponse(BaseModel):
    c_result_id: int
    c_id: int
    c_br_id: int
    speaking_speed: float
    silence: float
    clarity: float
    meaning_clarity: float
    cut: int
    curse: int
    filler: int
    biased: int
    slang: int
    speaking_speed_json: Optional[dict]
    silence_json: Optional[dict]
    clarity_json: Optional[dict]
    meaning_clarity_json: Optional[dict]
    cut_json: Optional[dict]
    summary: str
    advice: str
    created_at: datetime

    class Config:
        from_attributes = True


class CommunicationDetailResponse(BaseModel):
    c_id: int
    user_id: int
    status: str
    created_at: datetime
    voice_files: List[VoiceFileResponse]
    stt_results: List[STTResultResponse]
    script_sentences: List[CScriptSentenceResponse]
    bert_result: Optional[BERTResultResponse]
    result: Optional[AnalysisResultResponse]

    class Config:
        from_attributes = True