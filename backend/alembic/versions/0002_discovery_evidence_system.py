"""discovery evidence system schema

Revision ID: 0002_discovery_evidence_system
Revises: 0001_initial
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_discovery_evidence_system"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "candidate_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_type", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_role", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("raw_context_json", sa.Text(), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False),
        sa.Column("maturity_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Float(), nullable=False),
        sa.Column("next_due_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("entry_type", "name", "source", "source_url", name="uq_candidate_entry_source"),
    )
    op.create_index("ix_candidate_entries_entry_type", "candidate_entries", ["entry_type"])
    op.create_index("ix_candidate_entries_name", "candidate_entries", ["name"])
    op.create_index("ix_candidate_entries_source", "candidate_entries", ["source"])
    op.create_index("ix_candidate_entries_source_role", "candidate_entries", ["source_role"])
    op.create_index("ix_candidate_entries_status", "candidate_entries", ["status"])

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("raw_excerpt", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("content_hash", sa.String(length=120), nullable=False),
        sa.Column("raw_json", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("content_hash", name="uq_evidence_content_hash"),
    )
    op.create_index("ix_evidence_items_source_type", "evidence_items", ["source_type"])
    op.create_index("ix_evidence_items_source_name", "evidence_items", ["source_name"])
    op.create_index("ix_evidence_items_content_hash", "evidence_items", ["content_hash"])

    op.create_table(
        "evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidence_items.id"), nullable=False),
        sa.Column("target_type", sa.String(length=60), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("relation_type", sa.String(length=80), nullable=False),
        sa.Column("relation_reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("evidence_id", "target_type", "target_id", "relation_type", name="uq_evidence_link_target"),
    )
    op.create_index("ix_evidence_links_evidence_id", "evidence_links", ["evidence_id"])
    op.create_index("ix_evidence_links_target_type", "evidence_links", ["target_type"])
    op.create_index("ix_evidence_links_target_id", "evidence_links", ["target_id"])
    op.create_index("ix_evidence_links_relation_type", "evidence_links", ["relation_type"])

    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_role", sa.String(length=40), nullable=False),
        sa.Column("run_kind", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("inputs_json", sa.Text(), nullable=False),
        sa.Column("outputs_json", sa.Text(), nullable=False),
        sa.Column("candidates_created", sa.Integer(), nullable=False),
        sa.Column("evidence_created", sa.Integer(), nullable=False),
        sa.Column("keywords_promoted", sa.Integer(), nullable=False),
        sa.Column("cards_generated", sa.Integer(), nullable=False),
        sa.Column("actions_created", sa.Integer(), nullable=False),
        sa.Column("rejects_created", sa.Integer(), nullable=False),
        sa.Column("errors", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_source_runs_source", "source_runs", ["source"])
    op.create_index("ix_source_runs_source_role", "source_runs", ["source_role"])
    op.create_index("ix_source_runs_run_kind", "source_runs", ["run_kind"])
    op.create_index("ix_source_runs_status", "source_runs", ["status"])

    op.create_table(
        "watch_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_type", sa.String(length=60), nullable=False),
        sa.Column("target_key", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.Float(), nullable=False),
        sa.Column("cadence_hint", sa.String(length=40), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_due_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("raw_context_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("target_type", "target_key", "source_url", name="uq_watch_target"),
    )
    op.create_index("ix_watch_targets_target_type", "watch_targets", ["target_type"])
    op.create_index("ix_watch_targets_target_key", "watch_targets", ["target_key"])
    op.create_index("ix_watch_targets_status", "watch_targets", ["status"])

    op.create_table(
        "action_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=60), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("requested_by", sa.String(length=60), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("executed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_action_requests_action_type", "action_requests", ["action_type"])
    op.create_index("ix_action_requests_target_type", "action_requests", ["target_type"])
    op.create_index("ix_action_requests_target_id", "action_requests", ["target_id"])
    op.create_index("ix_action_requests_risk_level", "action_requests", ["risk_level"])
    op.create_index("ix_action_requests_status", "action_requests", ["status"])

    op.create_table(
        "action_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("action_requests.id"), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("target_type", sa.String(length=60), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_action_events_request_id", "action_events", ["request_id"])
    op.create_index("ix_action_events_event_type", "action_events", ["event_type"])
    op.create_index("ix_action_events_target_type", "action_events", ["target_type"])
    op.create_index("ix_action_events_target_id", "action_events", ["target_id"])

    op.create_table(
        "keyword_weight_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword_ref_type", sa.String(length=40), nullable=False),
        sa.Column("keyword_ref_id", sa.String(length=80), nullable=False),
        sa.Column("previous_weight", sa.Float(), nullable=False),
        sa.Column("new_weight", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_link_ids_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_keyword_weight_events_keyword_ref_type", "keyword_weight_events", ["keyword_ref_type"])
    op.create_index("ix_keyword_weight_events_keyword_ref_id", "keyword_weight_events", ["keyword_ref_id"])

    op.create_table(
        "opportunity_score_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opportunity_card_id", sa.Integer(), nullable=False),
        sa.Column("previous_score", sa.Float(), nullable=False),
        sa.Column("new_score", sa.Float(), nullable=False),
        sa.Column("previous_breakdown_json", sa.Text(), nullable=False),
        sa.Column("new_breakdown_json", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_link_ids_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_opportunity_score_events_opportunity_card_id", "opportunity_score_events", ["opportunity_card_id"])


def downgrade():
    op.drop_index("ix_opportunity_score_events_opportunity_card_id", table_name="opportunity_score_events")
    op.drop_table("opportunity_score_events")

    op.drop_index("ix_keyword_weight_events_keyword_ref_id", table_name="keyword_weight_events")
    op.drop_index("ix_keyword_weight_events_keyword_ref_type", table_name="keyword_weight_events")
    op.drop_table("keyword_weight_events")

    op.drop_index("ix_action_events_target_id", table_name="action_events")
    op.drop_index("ix_action_events_target_type", table_name="action_events")
    op.drop_index("ix_action_events_event_type", table_name="action_events")
    op.drop_index("ix_action_events_request_id", table_name="action_events")
    op.drop_table("action_events")

    op.drop_index("ix_action_requests_status", table_name="action_requests")
    op.drop_index("ix_action_requests_risk_level", table_name="action_requests")
    op.drop_index("ix_action_requests_target_id", table_name="action_requests")
    op.drop_index("ix_action_requests_target_type", table_name="action_requests")
    op.drop_index("ix_action_requests_action_type", table_name="action_requests")
    op.drop_table("action_requests")

    op.drop_index("ix_watch_targets_status", table_name="watch_targets")
    op.drop_index("ix_watch_targets_target_key", table_name="watch_targets")
    op.drop_index("ix_watch_targets_target_type", table_name="watch_targets")
    op.drop_table("watch_targets")

    op.drop_index("ix_source_runs_status", table_name="source_runs")
    op.drop_index("ix_source_runs_run_kind", table_name="source_runs")
    op.drop_index("ix_source_runs_source_role", table_name="source_runs")
    op.drop_index("ix_source_runs_source", table_name="source_runs")
    op.drop_table("source_runs")

    op.drop_index("ix_evidence_links_relation_type", table_name="evidence_links")
    op.drop_index("ix_evidence_links_target_id", table_name="evidence_links")
    op.drop_index("ix_evidence_links_target_type", table_name="evidence_links")
    op.drop_index("ix_evidence_links_evidence_id", table_name="evidence_links")
    op.drop_table("evidence_links")

    op.drop_index("ix_evidence_items_content_hash", table_name="evidence_items")
    op.drop_index("ix_evidence_items_source_name", table_name="evidence_items")
    op.drop_index("ix_evidence_items_source_type", table_name="evidence_items")
    op.drop_table("evidence_items")

    op.drop_index("ix_candidate_entries_status", table_name="candidate_entries")
    op.drop_index("ix_candidate_entries_source_role", table_name="candidate_entries")
    op.drop_index("ix_candidate_entries_source", table_name="candidate_entries")
    op.drop_index("ix_candidate_entries_name", table_name="candidate_entries")
    op.drop_index("ix_candidate_entries_entry_type", table_name="candidate_entries")
    op.drop_table("candidate_entries")
