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

    col_info   = {c["name"]: c for c in sa.inspect(conn).get_columns("documentchunk")}
    col_names  = set(col_info.keys())

    needs_embedding_json   = "embedding_json" not in col_names
    # alter_column sólo si vector_id existe Y todavía es NOT NULL
    needs_vector_id_fix    = (
        "vector_id" in col_names and
        col_info["vector_id"].get("nullable") is False
    )

    # Si el schema ya es correcto (creado por create_all), evitar batch_alter para
    # no generar lock exclusivo SQLite que bloquearía la conexión del vector_store.
    if not needs_embedding_json and not needs_vector_id_fix:
        return

    with op.batch_alter_table("documentchunk", schema=None) as batch_op:
        if needs_embedding_json:
            batch_op.add_column(
                sa.Column(
                    "embedding_json",
                    sa.Text(),
                    nullable=False,
                    server_default="[]",
                )
            )
        if needs_vector_id_fix:
            batch_op.alter_column(
                "vector_id",
                existing_type=sa.Integer(),
                nullable=True,
            )


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
