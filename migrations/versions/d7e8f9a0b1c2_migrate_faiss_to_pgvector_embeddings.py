"""Migrate FAISS to DB-backed vector embeddings (B2-FAISS fix)

Revision ID: d7e8f9a0b1c2
Revises: acefb4f68883
Create Date: 2026-06-14

Cambios:
- documentchunk.embedding_json: nueva columna TEXT para almacenar el vector float32
  serializado como JSON. Reemplaza el índice FAISS en disco.
- documentchunk.vector_id: pasa a nullable — ya no se usa como índice FAISS.
  Se conserva para no perder datos históricos.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "acefb4f68883"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    existing_tables = sa.inspect(conn).get_table_names()
    if "documentchunk" not in existing_tables:
        return

    col_info = {c["name"]: c for c in sa.inspect(conn).get_columns("documentchunk")}

    # op.add_column es DDL nativo de SQLite (sin rebuild de tabla ni lock exclusivo).
    # Seguro de ejecutar aunque haya otras conexiones abiertas al mismo archivo DB.
    if "embedding_json" not in col_info:
        op.add_column(
            "documentchunk",
            sa.Column("embedding_json", sa.Text(), nullable=False, server_default="[]"),
        )

    # alter_column para nullability SÍ requiere batch_alter (rebuild completo).
    # Solo se ejecuta si vector_id todavía está marcado NOT NULL en el schema real.
    # Si create_all creó la tabla con Optional[int], ya es nullable y se omite.
    col_info = {c["name"]: c for c in sa.inspect(conn).get_columns("documentchunk")}
    if "vector_id" in col_info and col_info["vector_id"].get("nullable") is False:
        with op.batch_alter_table("documentchunk", schema=None) as batch_op:
            batch_op.alter_column("vector_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    conn = op.get_bind()
    existing_tables = sa.inspect(conn).get_table_names()
    if "documentchunk" not in existing_tables:
        return

    existing_cols = [c["name"] for c in sa.inspect(conn).get_columns("documentchunk")]

    with op.batch_alter_table("documentchunk", schema=None) as batch_op:
        if "embedding_json" in existing_cols:
            batch_op.drop_column("embedding_json")
        if "vector_id" in existing_cols:
            batch_op.alter_column(
                "vector_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
