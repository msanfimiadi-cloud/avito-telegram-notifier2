"""create telegram chats table

Revision ID: 20260714_0001
Revises:
Create Date: 2026-07-14 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_chats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("chat_type", sa.String(length=32), nullable=False),
        sa.Column("registered_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("registered_by_username", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id"),
    )
    op.create_index(op.f("ix_telegram_chats_chat_id"), "telegram_chats", ["chat_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_telegram_chats_chat_id"), table_name="telegram_chats")
    op.drop_table("telegram_chats")
