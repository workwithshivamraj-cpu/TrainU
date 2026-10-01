"""Revocable login sessions and tenant retrieval indexes.

Revision ID: 92f67a531c10
Revises: 3fc92ab4e5e4
"""
from alembic import op
import sqlalchemy as sa

revision = "92f67a531c10"
down_revision = "3fc92ab4e5e4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_sources_org_status_created", "sources", ["organization_id", "status", "created_at"])
    op.create_index("ix_chunks_org_status", "transcript_chunks", ["organization_id", "source_status"])


def downgrade():
    op.drop_index("ix_chunks_org_status", table_name="transcript_chunks")
    op.drop_index("ix_sources_org_status_created", table_name="sources")
    op.drop_table("auth_sessions")
