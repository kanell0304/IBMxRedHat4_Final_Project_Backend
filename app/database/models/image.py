from sqlalchemy import Integer, String, LargeBinary
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base

class Image(Base):
    __tablename__ = "images"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary(length=10_485_760), nullable=False)
    
    # users: Mapped[list["User"]] = relationship("User", back_populates="profile_image")
