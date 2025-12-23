from sqlalchemy.ext.asyncio import AsyncSession
from ..models.image import Image


async def create_image(db: AsyncSession, filename: str, data: bytes) -> Image:
    image = Image(filename=filename, data=data)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image