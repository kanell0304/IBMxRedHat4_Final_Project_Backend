"""merge speed columns into speaking_speed

Revision ID: a3f8e9b2c1d4
Revises: bd20292fcd86
Create Date: 2025-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'a3f8e9b2c1d4'
down_revision: Union[str, Sequence[str], None] = 'bd20292fcd86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # 1. 새로운 컬럼 추가
    op.add_column('c_results', sa.Column('speaking_speed', sa.Float(), nullable=True))
    op.add_column('c_results', sa.Column('speaking_speed_json', sa.JSON(), nullable=True))

    # 2. JSON 컬럼들 추가 (기존 DB에 없었던 컬럼들)
    op.add_column('c_results', sa.Column('silence_json', sa.JSON(), nullable=True))
    op.add_column('c_results', sa.Column('clarity_json', sa.JSON(), nullable=True))
    op.add_column('c_results', sa.Column('meaning_clarity_json', sa.JSON(), nullable=True))
    op.add_column('c_results', sa.Column('cut_json', sa.JSON(), nullable=True))

    # 3. 기존 데이터 마이그레이션 (speed와 speech_rate의 평균을 speaking_speed로)
    connection.execute(sa.text("""
        UPDATE c_results
        SET speaking_speed = (speed + speech_rate) / 2
        WHERE speed IS NOT NULL AND speech_rate IS NOT NULL
    """))

    # 4. speaking_speed를 NOT NULL로 변경 (기본값 0.0 설정)
    connection.execute(sa.text("""
        UPDATE c_results
        SET speaking_speed = 0.0
        WHERE speaking_speed IS NULL
    """))
    op.alter_column('c_results', 'speaking_speed', nullable=False)

    # 5. 기존 컬럼 삭제
    op.drop_column('c_results', 'speech_rate')
    op.drop_column('c_results', 'speed')


def downgrade() -> None:
    connection = op.get_bind()

    # 1. 기존 컬럼 재생성
    op.add_column('c_results', sa.Column('speed', mysql.FLOAT(), nullable=True))
    op.add_column('c_results', sa.Column('speech_rate', mysql.FLOAT(), nullable=True))

    # 2. speaking_speed 데이터를 기존 컬럼으로 복사
    connection.execute(sa.text("""
        UPDATE c_results
        SET speed = speaking_speed,
            speech_rate = speaking_speed
        WHERE speaking_speed IS NOT NULL
    """))

    # 3. 기존 컬럼을 NOT NULL로 변경 (기본값 0.0 설정)
    connection.execute(sa.text("""
        UPDATE c_results
        SET speed = 0.0
        WHERE speed IS NULL
    """))
    connection.execute(sa.text("""
        UPDATE c_results
        SET speech_rate = 0.0
        WHERE speech_rate IS NULL
    """))
    op.alter_column('c_results', 'speed', nullable=False)
    op.alter_column('c_results', 'speech_rate', nullable=False)

    # 4. 새로운 컬럼 삭제
    op.drop_column('c_results', 'cut_json')
    op.drop_column('c_results', 'meaning_clarity_json')
    op.drop_column('c_results', 'clarity_json')
    op.drop_column('c_results', 'silence_json')
    op.drop_column('c_results', 'speaking_speed_json')
    op.drop_column('c_results', 'speaking_speed')
