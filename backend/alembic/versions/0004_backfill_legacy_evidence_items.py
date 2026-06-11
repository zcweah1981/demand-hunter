"""backfill legacy evidence items with old table columns

Revision ID: 0004_backfill_legacy_evidence_items
Revises: 0003_backfill_discovery_evidence
Create Date: 2026-06-11
"""
from alembic import op
from sqlalchemy import inspect

revision = "0004_backfill_legacy_evidence_items"
down_revision = "0003_backfill_discovery_evidence"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def upgrade():
    bind = op.get_bind()
    if not (_has_table("evidence_items") and _has_table("evidence_links")):
        return

    if _has_table("serp_results"):
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO evidence_items
                (target_type, target_id, evidence_source, evidence_role, classification, source_run_id, source_type, source_name, url, title, summary, raw_excerpt, confidence, content_hash, raw_json, captured_at)
            SELECT
                'keyword',
                CAST(keyword_id AS TEXT),
                'serp',
                'legacy_serp',
                'neutral',
                0,
                'serp',
                COALESCE(domain, ''),
                COALESCE(url, ''),
                COALESCE(title, ''),
                COALESCE(snippet, ''),
                COALESCE(snippet, ''),
                COALESCE(weakness_score, 0),
                'serp-' || id,
                json_object('keyword_id', keyword_id, 'rank', rank, 'gap_tags', COALESCE(gap_tags, '[]')),
                COALESCE(fetched_at, CURRENT_TIMESTAMP)
            FROM serp_results
            """
        )
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO evidence_links
                (evidence_id, target_type, target_id, relation_type, relation_reason, created_by, created_at)
            SELECT e.id, 'keyword', CAST(s.keyword_id AS TEXT), 'neutral', 'SERP result captured for this keyword', 'migration', COALESCE(s.fetched_at, CURRENT_TIMESTAMP)
            FROM serp_results s
            JOIN evidence_items e ON e.content_hash = 'serp-' || s.id
            """
        )

    if _has_table("social_evidence"):
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO evidence_items
                (target_type, target_id, evidence_source, evidence_role, classification, source_run_id, source_type, source_name, url, title, summary, raw_excerpt, confidence, content_hash, raw_json, captured_at)
            SELECT
                'keyword',
                CAST(keyword_id AS TEXT),
                'social',
                'legacy_social',
                'support',
                0,
                'social',
                COALESCE(platform, ''),
                COALESCE(url, ''),
                COALESCE(title, ''),
                COALESCE(snippet, ''),
                COALESCE(snippet, ''),
                0.55,
                'social-' || id,
                json_object('keyword_id', keyword_id, 'pain_tags', COALESCE(pain_tags, '[]')),
                COALESCE(collected_at, CURRENT_TIMESTAMP)
            FROM social_evidence
            """
        )
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO evidence_links
                (evidence_id, target_type, target_id, relation_type, relation_reason, created_by, created_at)
            SELECT e.id, 'keyword', CAST(s.keyword_id AS TEXT), 'support', 'Social discussion captured for this keyword', 'migration', COALESCE(s.collected_at, CURRENT_TIMESTAMP)
            FROM social_evidence s
            JOIN evidence_items e ON e.content_hash = 'social-' || s.id
            """
        )

    if _has_table("progress_evidence_items"):
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO evidence_items
                (target_type, target_id, evidence_source, evidence_role, classification, source_run_id, source_type, source_name, url, title, summary, raw_excerpt, confidence, content_hash, raw_json, captured_at)
            SELECT
                'progress_project',
                CAST(project_id AS TEXT),
                'progress',
                'legacy_progress',
                COALESCE(NULLIF(effect, ''), 'neutral'),
                0,
                'progress',
                COALESCE(source_domain, ''),
                COALESCE(url, ''),
                COALESCE(title, ''),
                COALESCE(snippet, ''),
                COALESCE(snippet, ''),
                COALESCE(confidence, 0),
                'progress-' || id,
                json_object('project_id', project_id, 'hypothesis_id', hypothesis_id, 'task_id', task_id, 'effect', COALESCE(effect, 'neutral'), 'reason', COALESCE(reason, '')),
                COALESCE(captured_at, CURRENT_TIMESTAMP)
            FROM progress_evidence_items
            """
        )
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO evidence_links
                (evidence_id, target_type, target_id, relation_type, relation_reason, created_by, created_at)
            SELECT e.id, 'progress_project', CAST(p.project_id AS TEXT), COALESCE(NULLIF(p.effect, ''), 'neutral'), COALESCE(p.reason, 'Progress evidence captured for this project'), 'migration', COALESCE(p.captured_at, CURRENT_TIMESTAMP)
            FROM progress_evidence_items p
            JOIN evidence_items e ON e.content_hash = 'progress-' || p.id
            """
        )


def downgrade():
    pass
