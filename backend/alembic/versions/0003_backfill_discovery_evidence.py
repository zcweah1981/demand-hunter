"""backfill discovery evidence data

Revision ID: 0003_backfill_discovery_evidence
Revises: 0002_discovery_evidence_system
Create Date: 2026-06-11
"""
from alembic import op
from sqlalchemy import inspect

revision = "0003_backfill_discovery_evidence"
down_revision = "0002_discovery_evidence_system"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return name in inspect(op.get_bind()).get_table_names()


def upgrade():
    bind = op.get_bind()

    if _has_table("candidate_keywords") and _has_table("candidate_entries"):
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO candidate_entries
                (entry_type, name, source, source_role, source_url, raw_context_json, trend_score, maturity_type, status, priority, next_due_at, created_at, updated_at)
            SELECT
                'keyword',
                COALESCE(NULLIF(keyword, ''), 'candidate-' || id),
                COALESCE(source, ''),
                COALESCE(NULLIF(source_role, ''), 'legacy_candidate_keyword'),
                COALESCE(source_url, ''),
                COALESCE(NULLIF(evidence_json, ''), '{}'),
                COALESCE(score, 0),
                COALESCE(NULLIF(maturity_type, ''), 'unknown'),
                CASE
                    WHEN COALESCE(quality_gate_status, '') IN ('passed', 'promoted') THEN 'scored'
                    WHEN COALESCE(evidence_status, '') IN ('missing', 'needs_evidence') THEN 'needs_evidence'
                    ELSE 'new'
                END,
                COALESCE(score, 0) * 100,
                NULL,
                COALESCE(created_at, CURRENT_TIMESTAMP),
                COALESCE(created_at, CURRENT_TIMESTAMP)
            FROM candidate_keywords
            WHERE COALESCE(keyword, '') <> ''
            """
        )

    if _has_table("keywords") and _has_table("candidate_entries"):
        bind.exec_driver_sql(
            """
            INSERT OR IGNORE INTO candidate_entries
                (entry_type, name, source, source_role, source_url, raw_context_json, trend_score, maturity_type, status, priority, next_due_at, created_at, updated_at)
            SELECT
                'demand',
                COALESCE(NULLIF(query, ''), 'keyword-' || id),
                COALESCE(source, ''),
                'legacy_keyword_library',
                '',
                json_object('keyword_id', id, 'intent', COALESCE(intent, ''), 'root_terms', COALESCE(root_terms, '[]')),
                COALESCE(score, 0),
                'mature_keyword',
                'scored',
                COALESCE(score, 0) * 100,
                NULL,
                COALESCE(created_at, CURRENT_TIMESTAMP),
                COALESCE(created_at, CURRENT_TIMESTAMP)
            FROM keywords
            WHERE COALESCE(query, '') <> ''
            """
        )

    if _has_table("serp_results") and _has_table("evidence_items"):
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

    if _has_table("social_evidence") and _has_table("evidence_items"):
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

    if _has_table("progress_evidence_items") and _has_table("evidence_items"):
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
