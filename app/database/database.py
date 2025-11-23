from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from app.database.base import Base

load_dotenv()

DATABASE_URL=os.getenv("DB_URL")


engine=create_engine(
    DATABASE_URL, 
    pool_pre_ping=True,
    )

SessionLocal=sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine)


def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    try:
        import app.database.models.interviews
        import app.database.models.i_answers
        import app.database.models.i_final_results
        import app.database.models.i_question_results
        import app.database.models.i_questions

        Base.metadata.create_all(bind=engine)
        print("데이터베이스 테이블 생성")
        
    except Exception as e:
        print(f"테이블 생성 실패: {e}")