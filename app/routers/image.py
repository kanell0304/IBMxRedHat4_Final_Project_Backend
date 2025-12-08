from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.database import get_db
from backend.app.database.schemas.image import ImageResponse
from backend.app.service.image_service import ImageService

router = APIRouter(prefix="/image", tags=["Image"])

# 이미지 업로드
@router.post("/upload", response_model=ImageResponse)
async def upload_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    result = await ImageService.image_upload(file, db)
    return result

# 이미지 조회
@router.get("/{image_id}")
async def get_image_by_id(image_id: int, db: AsyncSession = Depends(get_db)):
    result = await ImageService.get_image(image_id, db)
    return result

# 이미지 원본 보여주기
@router.get("/raw/{image_id}")
async def get_image_raw_by_id(image_id: int, db: AsyncSession = Depends(get_db)):
    result = await ImageService.get_image_raw(image_id, db)
    return result
