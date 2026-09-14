"""Create practice_sessions and weak_words tables.

Revision ID: 0004_practice_sessions_and_weak_words
Revises: 0003_enrichment_stage_and_error_message
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "0004_practice_sessions_and_weak_words"
down_revision: Union[str, Sequence[str], None] = "0003_enrichment_stage_and_error_message"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create practice_sessions and weak_words tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "practice_sessions" not in existing_tables:
        op.create_table(
            "practice_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.String(), nullable=False),
            sa.Column("text_id", sa.Integer(), nullable=False),
            sa.Column("sentence_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sentence_text", sa.String(), nullable=False, server_default=""),
            sa.Column("target_type", sa.String(), nullable=False, server_default="original"),
            sa.Column("net_wpm", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("raw_wpm", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("accuracy", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("active_seconds", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("mistake_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("mistakes_detail", sa.JSON(), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["text_id"], ["texts.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_practice_sessions_owner_id", "practice_sessions", ["owner_id"])
        op.create_index("ix_practice_sessions_text_id", "practice_sessions", ["text_id"])
        op.create_index("ix_practice_sessions_completed_at", "practice_sessions", ["completed_at"])
        op.create_index(
            "ix_practice_sessions_owner_completed",
            "practice_sessions",
            ["owner_id", "completed_at"],
        )
        op.create_index(
            "ix_practice_sessions_owner_text",
            "practice_sessions",
            ["owner_id", "text_id"],
        )

    if "weak_words" not in existing_tables:
        op.create_table(
            "weak_words",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("owner_id", sa.String(), nullable=False),
            sa.Column("language", sa.String(), nullable=False, server_default="Unknown"),
            sa.Column("word", sa.String(), nullable=False),
            sa.Column("mistake_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("practice_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_mistake_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", "language", "word", name="uq_weak_words_owner_lang_word"),
        )
        op.create_index("ix_weak_words_owner_id", "weak_words", ["owner_id"])
        op.create_index("ix_weak_words_language", "weak_words", ["language"])
        op.create_index("ix_weak_words_word", "weak_words", ["word"])
        op.create_index("ix_weak_words_owner_mistakes", "weak_words", ["owner_id", "mistake_count"])


def downgrade() -> None:
    """Drop practice_sessions and weak_words tables."""
    op.drop_table("weak_words")
    op.drop_table("practice_sessions")
