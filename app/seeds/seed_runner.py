import os
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session

def _seed_enabled() -> bool:
    return (
        os.getenv("APP_ENV", "").lower() in {"local", "dev"}
        and os.getenv("AUTO_SEED", "false").lower() in {"1", "true", "yes", "y"}
    )

def run_seed_if_needed(db: Session) -> None:
    """로컬에서만: main_category가 비어있으면 seed.sql 실행"""
    if not _seed_enabled():
        return

    exists = db.execute(text("SELECT 1 FROM main_category LIMIT 1")).first()
    if exists is not None:
        return

    seed_file = Path(__file__).resolve().parent / "seed.sql"
    sql = seed_file.read_text(encoding="utf-8")

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        db.execute(text(stmt))

    db.commit()
