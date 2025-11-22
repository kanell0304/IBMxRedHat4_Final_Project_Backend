from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.mysql import LONGBLOB
from ..base import Base

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False) # 이미지 이름
    data = Column(LONGBLOB, nullable=False) # 이미지 정보
