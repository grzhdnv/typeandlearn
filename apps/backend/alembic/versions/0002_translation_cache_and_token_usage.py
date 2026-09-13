"""Create translation_cache and token_usage_records tables.

Revision ID: 0002_translation_cache_and_token_usage
Revises: 0001_initial_schema_with_owner
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "0002_translation_cache_and_token_usage"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema_with_owner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create translation_cache and token_usage_records tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "translation_cache" not in existing_tables:
        op.create_table(
            "translation_cache",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("source_language", sa.String(), nullable=False),
            sa.Column("target_language", sa.String(), nullable=False, server_default="English"),
            sa.Column("sentence_hash", sa.String(), nullable=False),
            sa.Column("prompt_version", sa.String(), nullable=False, server_default="v1"),
            sa.Column("translation", sa.String(), nullable=False),
            sa.Column("translation_hints", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "source_language",
                "target_language",
                "sentence_hash",
                "prompt_version",
                name="uq_translation_cache_key",
            ),
        )
        op.create_index("ix_translation_cache_source_language", "translation_cache", ["source_language"])
        op.create_index("ix_translation_cache_target_language", "translation_cache", ["target_language"])
        op.create_index("ix_translation_cache_sentence_hash", "translation_cache", ["sentence_hash"])
        op.create_index("ix_translation_cache_prompt_version", "translation_cache", ["prompt_version"])

    if "token_usage_records" not in existing_tables:
        op.create_table(
            "token_usage_records",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("owner_id", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_token_usage_records_owner_id", "token_usage_records", ["owner_id"])
        op.create_index("ix_token_usage_records_provider", "token_usage_records", ["provider"])
        op.create_index("ix_token_usage_records_model", "token_usage_records", ["model"])
        op.create_index("ix_token_usage_records_created_at", "token_usage_records", ["created_at"])


def downgrade() -> None:
    """Drop translation_cache and token_usage_records tables."""
    op.drop_table("token_usage_records")
    op.drop_table("translation_cache")
