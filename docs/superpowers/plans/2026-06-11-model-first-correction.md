# Model-First Discovery Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correct the first refactor pass so existing discovery models are the primary loop: model -> evidence -> entries/keywords/opportunities -> model feedback.

**Architecture:** Keep the current database tables. Add an interpretation layer that groups source runs, evidence, entries, keywords, and cards by model. Move model explanations into Evidence System, and keep Source Performance as an effectiveness view only.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Next.js App Router, React, TypeScript, Tailwind CSS.

---

## File Structure

- Modify: `docs/DISCOVERY_EVIDENCE_SYSTEM_REFACTOR_V2.md`
  Record the confirmed model-first principle and UI boundaries.
- Create: `backend/app/evidence_models.py`
  Central model catalog and aggregate statistics from existing tables.
- Modify: `backend/app/api/v1/endpoints/evidence.py`
  Add `/api/evidence/models` and `/api/evidence/models/{model_id}`.
- Modify: `backend/tests/test_evidence_system.py`
  Cover model catalog placement and source-to-model grouping.
- Modify: `frontend/lib/api.ts`
  Add evidence model API types.
- Modify: `frontend/components/Nav.tsx`
  Add `证据模型` under Evidence System and move Source Performance to a pure discovery effectiveness page.
- Create: `frontend/app/evidence/models/page.tsx`
  Model overview page.
- Create: `frontend/app/evidence/models/[modelId]/page.tsx`
  Model detail page.
- Modify: `frontend/app/evidence/page.tsx`
  Link to model overview.
- Modify: `frontend/components/CollectorsPage.tsx`
  Remove model directory cards from Source Performance and show only effectiveness.

## Tasks

- [x] Add tests for model catalog and source mapping.
- [x] Add backend model aggregation service.
- [x] Expose model aggregation APIs.
- [x] Wire frontend API types.
- [x] Add Evidence System model pages.
- [x] Convert Source Performance into effectiveness-only page.
- [x] Update the refactor document with model-first boundaries.
- [x] Run backend tests and frontend build.
