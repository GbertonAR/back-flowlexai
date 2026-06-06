"""Add Legislative Ontology Layer 1 and 2

Revision ID: acefb4f68883
Revises: f4ffa005e048
Create Date: 2026-05-06 14:41:25.376551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'acefb4f68883'
down_revision: Union[str, Sequence[str], None] = 'f4ffa005e048'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    existing = sa.inspect(conn).get_table_names()

    if 'bloque' not in existing:
        op.create_table('bloque',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sigla', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('color_hex', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_bloque_nombre'), 'bloque', ['nombre'], unique=False)
        op.create_index(op.f('ix_bloque_tenant_id'), 'bloque', ['tenant_id'], unique=False)

    if 'comision' not in existing:
        op.create_table('comision',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('descripcion', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('es_permanente', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_comision_nombre'), 'comision', ['nombre'], unique=False)
        op.create_index(op.f('ix_comision_tenant_id'), 'comision', ['tenant_id'], unique=False)

    if 'tiponorma' not in existing:
        op.create_table('tiponorma',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_tiponorma_tenant_id'), 'tiponorma', ['tenant_id'], unique=False)

    if 'legislador' not in existing:
        op.create_table('legislador',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bloque_id', sa.Integer(), nullable=True),
        sa.Column('distrito', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('biografia', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['bloque_id'], ['bloque.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['lexia_user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
        )

    if 'proyecto' not in existing:
        op.create_table('proyecto',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('numero_expediente', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('titulo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sumario', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('texto_completo', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('fecha_ingreso', sa.DateTime(), nullable=False),
        sa.Column('estado', sa.Enum('INGRESO', 'COMISION', 'DICTAMEN', 'SESION', 'VOTACION', 'APROBADO', 'RECHAZADO', 'ARCHIVADO', name='estadoexpediente'), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('autor_id', sa.Integer(), nullable=False),
        sa.Column('tipo_norma_id', sa.Integer(), nullable=False),
        sa.Column('jurisdiccion', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('vigente', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['autor_id'], ['legislador.id'], ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ),
        sa.ForeignKeyConstraint(['tipo_norma_id'], ['tiponorma.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_proyecto_numero_expediente'), 'proyecto', ['numero_expediente'], unique=False)
        op.create_index(op.f('ix_proyecto_tenant_id'), 'proyecto', ['tenant_id'], unique=False)
        op.create_index(op.f('ix_proyecto_titulo'), 'proyecto', ['titulo'], unique=False)

    if 'dictamen' not in existing:
        op.create_table('dictamen',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('proyecto_id', sa.Integer(), nullable=False),
        sa.Column('comision_id', sa.Integer(), nullable=False),
        sa.Column('texto', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fecha', sa.DateTime(), nullable=False),
        sa.Column('tipo_dictamen', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['comision_id'], ['comision.id'], ),
        sa.ForeignKeyConstraint(['proyecto_id'], ['proyecto.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
    conn = op.get_bind()
    existing_cols = [c['name'] for c in sa.inspect(conn).get_columns('auditorialog')]
    with op.batch_alter_table('auditorialog', schema=None) as batch_op:
        if 'content_hash' in existing_cols:
            batch_op.alter_column('content_hash',
                   existing_type=sa.TEXT(),
                   type_=sqlmodel.sql.sqltypes.AutoString(),
                   existing_nullable=True)
        else:
            batch_op.add_column(sa.Column('content_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    tenant_cols = [c['name'] for c in sa.inspect(conn).get_columns('tenant')]
    if 'configuration' not in tenant_cols:
        op.add_column('tenant', sa.Column('configuration', sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tenant', 'configuration')
    with op.batch_alter_table('auditorialog', schema=None) as batch_op:
        batch_op.alter_column('content_hash',
               existing_type=sqlmodel.sql.sqltypes.AutoString(),
               type_=sa.TEXT(),
               existing_nullable=True)

    op.drop_table('dictamen')
    op.drop_index(op.f('ix_proyecto_titulo'), table_name='proyecto')
    op.drop_index(op.f('ix_proyecto_tenant_id'), table_name='proyecto')
    op.drop_index(op.f('ix_proyecto_numero_expediente'), table_name='proyecto')
    op.drop_table('proyecto')
    op.drop_table('legislador')
    op.drop_index(op.f('ix_tiponorma_tenant_id'), table_name='tiponorma')
    op.drop_table('tiponorma')
    op.drop_index(op.f('ix_comision_tenant_id'), table_name='comision')
    op.drop_index(op.f('ix_comision_nombre'), table_name='comision')
    op.drop_table('comision')
    op.drop_index(op.f('ix_bloque_tenant_id'), table_name='bloque')
    op.drop_index(op.f('ix_bloque_nombre'), table_name='bloque')
    op.drop_table('bloque')
    # ### end Alembic commands ###
