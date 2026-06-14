"""add action request runtime fields

Revision ID: 0005_action_request_runtime_fields
Revises: 0004_backfill_legacy_evidence_items
Create Date: 2026-06-13
"""
from alembic import op
from sqlalchemy import inspect

revision = "0005_action_request_runtime_fields"
down_revision = "0004_backfill_legacy_evidence_items"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {col["name"] for col in inspect(op.get_bind()).get_columns(table)}


def _add_column_sql(sql: str, column: str) -> None:
    if not _has_column("action_requests", column):
        op.get_bind().exec_driver_sql(sql)


def upgrade():
    if not _has_table("action_requests"):
        return
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN run_id INTEGER", "run_id")
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN payload_json TEXT DEFAULT '{}'", "payload_json")
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN error_json TEXT DEFAULT '{}'", "error_json")
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN retry_count INTEGER DEFAULT 0", "retry_count")
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN max_retries INTEGER DEFAULT 3", "max_retries")
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN started_at DATETIME", "started_at")
    _add_column_sql("ALTER TABLE action_requests ADD COLUMN finished_at DATETIME", "finished_at")


def downgrade():
    pass
