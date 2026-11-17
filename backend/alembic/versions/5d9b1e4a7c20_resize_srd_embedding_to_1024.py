"""resize srd embedding to 1024

Revision ID: 5d9b1e4a7c20
Revises: 175758c1f0d3
Create Date: 2026-11-17 00:05:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d9b1e4a7c20"
down_revision: str | Sequence[str] | None = "175758c1f0d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VECTOR_SIZE = 1024


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_srd_chunks_embedding_hnsw")
    op.execute(
        "ALTER TABLE srd_chunks "
        f"ALTER COLUMN embedding TYPE vector({VECTOR_SIZE}) "
        f"USING embedding::vector({VECTOR_SIZE})"
    )
    op.create_index(
        "ix_srd_chunks_embedding_hnsw",
        "srd_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    # Векторы другой размерности нельзя преобразовать обратно, поэтому
    # корпус очищается: после отката выполните импорт SRD заново.
    op.execute("DROP INDEX IF EXISTS ix_srd_chunks_embedding_hnsw")
    op.execute("TRUNCATE TABLE srd_chunks")
    op.execute(
        "ALTER TABLE srd_chunks "
        "ALTER COLUMN embedding TYPE vector(1536) "
        "USING embedding::vector(1536)"
    )
    op.create_index(
        "ix_srd_chunks_embedding_hnsw",
        "srd_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
