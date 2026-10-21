"""Persist source and preparation checkpoints before background NLP.

Revision ID: 0006_durable_intake
Revises: 0005_provider_governance
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_durable_intake"
down_revision = "0005_provider_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("texts")}
    with op.batch_alter_table("texts") as batch:
        if "source_text" not in columns:
            batch.add_column(sa.Column("source_text", sa.String(), nullable=True))
        if "intake_options" not in columns:
            batch.add_column(sa.Column("intake_options", sa.JSON(), nullable=True))


def downgrade() -> None:
    # Compatibility rollback keeps immutable uploaded sources and preparation
    # checkpoints in additive nullable columns; the previous app ignores them.
    # Dropping them would destroy queued uploads that have no sentences yet.
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("texts")}
    if "source_text" in columns:
        unprepared = bind.execute(sa.text("SELECT COUNT(*) FROM texts WHERE source_text IS NOT NULL AND total_sentences = 0")).scalar()
        if unprepared:
            raise RuntimeError("Prepare or explicitly delete pending uploads before downgrading; saved sources are preserved")
