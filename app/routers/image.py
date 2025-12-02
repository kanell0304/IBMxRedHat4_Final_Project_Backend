from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_db
from app.database.crud import image as crud
from app.database.schemas.image import ImageUploadResponse

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    image_data = await file.read()
    image = await crud.create_image(db, filename=file.filename, data=image_data)
    return image