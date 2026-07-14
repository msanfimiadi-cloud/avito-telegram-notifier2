"""create avito accounts

Revision ID: 20260714_0002
Revises: 20260714_0001
Create Date: 2026-07-14 00:02:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0002"
down_revision: str | None = "20260714_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "avito_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("profile_id", sa.BigInteger(), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("client_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("token_status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("last_token_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_token_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_avito_accounts_client_id"),
        sa.UniqueConstraint("profile_id", name="uq_avito_accounts_profile_id"),
    )
    op.create_index(op.f("ix_avito_accounts_client_id"), "avito_accounts", ["client_id"], unique=False)
    op.create_index(op.f("ix_avito_accounts_profile_id"), "avito_accounts", ["profile_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_avito_accounts_profile_id"), table_name="avito_accounts")
    op.drop_index(op.f("ix_avito_accounts_client_id"), table_name="avito_accounts")
    op.drop_table("avito_accounts")
