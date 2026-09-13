"""Initial schema baseline with mandatory owner_id and background_jobs table.

Revision ID: 0001_initial_schema_with_owner
Revises:
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "0001_initial_schema_with_owner"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create or upgrade tables to include owner_id and background_jobs."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. texts table
    if "texts" not in existing_tables:
        op.create_table(
            "texts",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default"),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("language", sa.String(), nullable=False, server_default="Unknown"),
            sa.Column("difficulty_level", sa.String(), nullable=False, server_default="Unrated"),
            sa.Column("author", sa.String(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_sentences", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("completed_sentence_indices", sa.JSON(), nullable=True),
            sa.Column("total_sentences", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("estimated_time_minutes", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_texts_owner_id", "texts", ["owner_id"])
        op.create_index("ix_texts_owner_id_id", "texts", ["owner_id", "id"])
        op.create_index("ix_texts_title", "texts", ["title"])
        op.create_index("ix_texts_status", "texts", ["status"])
        op.create_index("ix_texts_language", "texts", ["language"])
        op.create_index("ix_texts_difficulty_level", "texts", ["difficulty_level"])
        op.create_index("ix_texts_author", "texts", ["author"])
        op.create_index("ix_texts_category", "texts", ["category"])
    else:
        columns = {col["name"] for col in inspector.get_columns("texts")}
        with op.batch_alter_table("texts") as batch_op:
            if "owner_id" not in columns:
                batch_op.add_column(
                    sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default")
                )
                batch_op.create_index("ix_texts_owner_id", ["owner_id"])
                batch_op.create_index("ix_texts_owner_id_id", ["owner_id", "id"])

    # 2. sentences table
    if "sentences" not in existing_tables:
        op.create_table(
            "sentences",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default"),
            sa.Column("text_id", sa.Integer(), sa.ForeignKey("texts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("paragraph_index", sa.Integer(), nullable=False),
            sa.Column("sentence_index", sa.Integer(), nullable=False),
            sa.Column("original_text", sa.String(), nullable=False),
            sa.Column("translation", sa.String(), nullable=True),
            sa.Column("translation_hints", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        )
        op.create_index("ix_sentences_owner_id", "sentences", ["owner_id"])
        op.create_index("ix_sentences_owner_id_text_id", "sentences", ["owner_id", "text_id"])
        op.create_index("ix_sentences_text_id", "sentences", ["text_id"])
        op.create_index("ix_sentences_status", "sentences", ["status"])
    else:
        columns = {col["name"] for col in inspector.get_columns("sentences")}
        with op.batch_alter_table("sentences") as batch_op:
            if "owner_id" not in columns:
                batch_op.add_column(
                    sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default")
                )
                batch_op.create_index("ix_sentences_owner_id", ["owner_id"])
                batch_op.create_index("ix_sentences_owner_id_text_id", ["owner_id", "text_id"])

    # 3. word_frequencies table
    if "word_frequencies" not in existing_tables:
        op.create_table(
            "word_frequencies",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default"),
            sa.Column("text_id", sa.Integer(), sa.ForeignKey("texts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("word", sa.String(), nullable=False),
            sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("translation", sa.String(), nullable=True),
        )
        op.create_index("ix_word_frequencies_owner_id", "word_frequencies", ["owner_id"])
        op.create_index("ix_word_frequencies_text_id", "word_frequencies", ["text_id"])
        op.create_index("ix_word_frequencies_word", "word_frequencies", ["word"])
    else:
        columns = {col["name"] for col in inspector.get_columns("word_frequencies")}
        with op.batch_alter_table("word_frequencies") as batch_op:
            if "owner_id" not in columns:
                batch_op.add_column(
                    sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default")
                )
                batch_op.create_index("ix_word_frequencies_owner_id", ["owner_id"])

    # 4. practice_sentences table
    if "practice_sentences" not in existing_tables:
        op.create_table(
            "practice_sentences",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default"),
            sa.Column("text_id", sa.Integer(), sa.ForeignKey("texts.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sentence_index", sa.Integer(), nullable=False),
            sa.Column("sentence", sa.String(), nullable=False),
            sa.Column("translation", sa.String(), nullable=False),
            sa.Column("translation_hints", sa.JSON(), nullable=True),
        )
        op.create_index("ix_practice_sentences_owner_id", "practice_sentences", ["owner_id"])
        op.create_index("ix_practice_sentences_text_id", "practice_sentences", ["text_id"])
    else:
        columns = {col["name"] for col in inspector.get_columns("practice_sentences")}
        with op.batch_alter_table("practice_sentences") as batch_op:
            if "owner_id" not in columns:
                batch_op.add_column(
                    sa.Column("owner_id", sa.String(), nullable=False, server_default="owner_local_default")
                )
                batch_op.create_index("ix_practice_sentences_owner_id", ["owner_id"])

    # 5. background_jobs table
    if "background_jobs" not in existing_tables:
        op.create_table(
            "background_jobs",
            sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
            sa.Column("owner_id", sa.String(), nullable=False),
            sa.Column("text_id", sa.Integer(), sa.ForeignKey("texts.id", ondelete="CASCADE"), nullable=True),
            sa.Column("task_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("worker_id", sa.String(), nullable=True),
            sa.Column("error_message", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_background_jobs_owner_id", "background_jobs", ["owner_id"])
        op.create_index("ix_background_jobs_text_id", "background_jobs", ["text_id"])
        op.create_index("ix_background_jobs_task_type", "background_jobs", ["task_type"])
        op.create_index("ix_background_jobs_status", "background_jobs", ["status"])
        op.create_index("ix_background_jobs_leased_until", "background_jobs", ["leased_until"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("background_jobs")
    op.drop_table("practice_sentences")
    op.drop_table("word_frequencies")
    op.drop_table("sentences")
    op.drop_table("texts")
