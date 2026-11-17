"""Corrige campos da tabela triagens.

Revision ID: 7d88961943cd
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "7d88961943cd"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns("triagens")
    }

    with op.batch_alter_table("triagens") as batch_op:
        if "relato" in colunas and "texto_sintomas" not in colunas:
            batch_op.alter_column(
                "relato",
                new_column_name="texto_sintomas",
                existing_type=sa.Text(),
                existing_nullable=False,
            )

        if "urgencia" not in colunas:
            batch_op.add_column(
                sa.Column(
                    "urgencia",
                    sa.String(length=30),
                    nullable=False,
                    server_default="baixa",
                )
            )

        if "especialidade" not in colunas:
            batch_op.add_column(
                sa.Column(
                    "especialidade",
                    sa.String(length=100),
                    nullable=False,
                    server_default="clinica_geral",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    colunas = {
        coluna["name"]
        for coluna in inspector.get_columns("triagens")
    }

    with op.batch_alter_table("triagens") as batch_op:
        if "especialidade" in colunas:
            batch_op.drop_column("especialidade")

        if "urgencia" in colunas:
            batch_op.drop_column("urgencia")

        if "texto_sintomas" in colunas and "relato" not in colunas:
            batch_op.alter_column(
                "texto_sintomas",
                new_column_name="relato",
                existing_type=sa.Text(),
                existing_nullable=False,
            )