"""Shared provider quotas and paid-fallback reservations.

Revision ID: 0005_provider_governance
Revises: 0004_practice_sessions_and_weak_words
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_provider_governance"
down_revision = "0004_practice_sessions_and_weak_words"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "provider_gates" not in existing:
        op.create_table(
            "provider_gates",
            sa.Column("provider", sa.String(), primary_key=True),
            sa.Column("cooldown_until", sa.Float(), nullable=False),
            sa.Column("tokens_reset_at", sa.Float(), nullable=False),
            sa.Column("requests_reset_at", sa.Float(), nullable=False),
            sa.Column("tokens_remaining", sa.Integer(), nullable=True),
            sa.Column("requests_remaining", sa.Integer(), nullable=True),
        )
    if "provider_calls" not in existing:
        op.create_table(
            "provider_calls",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("owner_id", sa.String(), nullable=False),
            sa.Column("task", sa.String(), nullable=False),
            sa.Column("created_at", sa.Float(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("tokens", sa.Integer(), nullable=False),
            sa.Column("cost_microusd", sa.Integer(), nullable=False),
            sa.Column("response_model", sa.String(), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=True),
        )
        for column in ("provider", "owner_id", "created_at"):
            op.create_index(f"ix_provider_calls_{column}", "provider_calls", [column])


def downgrade() -> None:
    op.drop_table("provider_calls")
    op.drop_table("provider_gates")
