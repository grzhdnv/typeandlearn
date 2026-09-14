"""Add enrichment_stage and error_message to texts table.

Revision ID: 0003_enrichment_stage_and_error_message
Revises: 0002_translation_cache_and_token_usage
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "0003_enrichment_stage_and_error_message"
down_revision: Union[str, Sequence[str], None] = "0002_translation_cache_and_token_usage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add enrichment_stage and error_message columns to texts table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("texts")}

    if "enrichment_stage" not in existing_columns:
        op.add_column(
            "texts",
            sa.Column("enrichment_stage", sa.String(), nullable=True, server_default="queued"),
        )
        op.create_index("ix_texts_enrichment_stage", "texts", ["enrichment_stage"])

    if "error_message" not in existing_columns:
        op.add_column(
            "texts",
            sa.Column("error_message", sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Remove enrichment_stage and error_message columns from texts table."""
    op.drop_index("ix_texts_enrichment_stage", table_name="texts")
    op.drop_column("texts", "error_message")
    op.drop_column("texts", "enrichment_stage")
