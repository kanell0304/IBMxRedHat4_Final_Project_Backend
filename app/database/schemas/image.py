from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    id: int
    filename: str
    
    class Config:
        from_attributes = True