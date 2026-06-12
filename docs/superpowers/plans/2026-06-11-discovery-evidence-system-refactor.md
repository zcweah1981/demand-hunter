# Discovery Evidence System Refactor Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the confirmed V2 architecture: independent evidence system, candidate entries, demand/trend split scoring, objective evidence links, unified automation cycle, and context-aware manual actions.

**Architecture:** Implement this as staged vertical slices. Start with data contracts and APIs, then wire services into existing collectors/Four-Find/progress flows, then update navigation/pages. Keep evidence objective: `evidence_items` stores facts, `evidence_links` records who the evidence serves, and scoring/weight changes live in separate event tables.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, Pydantic, Next.js App Router, React, TypeScript, Tailwind CSS.

---

## Scope Check

This refactor spans discovery, evidence, automation, scoring, and UI. Treat it as one program with testable phases, not one giant commit. Each chunk below must leave the app runnable.

Do not implement the whole plan in one pass. Complete one chunk, verify, commit, then continue.

Primary spec:

- `docs/DISCOVERY_EVIDENCE_SYSTEM_REFACTOR_V2.md`

Current code anchors:

- Backend models: `backend/app/models.py`
- API router: `backend/app/api/v1/api.py`
- Collectors: `backend/app/collectors.py`
- Four-Find: `backend/app/four_find.py`
- Runtime loop: `backend/app/main_runtime.py`
- Existing pages/nav: `frontend/components/Nav.tsx`, `frontend/app/**/page.tsx`

Verification baseline:

```powershell
cd D:\Projects\damand-hunter
backend\.venv\Scripts\python.exe -m compileall backend\app
cd frontend
npm run build
```

---

## File Structure

### Backend Files

- Modify: `backend/app/models.py`  
  Add new SQLAlchemy models: `CandidateEntry`, `EvidenceItem`, `EvidenceLink`, `SourceRun`, `WatchTarget`, `ActionRequest`, `ActionEvent`, `KeywordWeightEvent`, `OpportunityScoreEvent`.

- Create: `backend/alembic/versions/0002_discovery_evidence_system.py`  
  Migration for new tables and safe nullable columns on existing tables.

- Create: `backend/app/discovery_entries.py`  
  Candidate entry creation, routing, dedupe, and derived-entry backflow.

- Create: `backend/app/evidence_system.py`  
  Objective evidence capture, linking, service relationship updates, evidence timeline queries.

- Create: `backend/app/scoring_system.py`  
  Demand keyword scoring, trend entity scoring, keyword quality gate, event recording.

- Create: `backend/app/automation_cycle.py`  
  Unified automatic cycle. It collects due actions from all objects, prioritizes, executes, and schedules next actions.

- Create: `backend/app/action_requests.py`  
  Context-aware manual actions. Buttons create action requests; service maps them into low/medium/high risk execution.

- Create: `backend/app/api/v1/endpoints/entries.py`  
  Candidate entry APIs.

- Create: `backend/app/api/v1/endpoints/evidence.py`  
  Evidence items, links, tasks, timelines, and backflow APIs.

- Create: `backend/app/api/v1/endpoints/automation_cycle.py`  
  Unified run, due actions, action request, and repair APIs.

- Modify: `backend/app/api/v1/api.py`  
  Register new routers.

- Modify: `backend/app/collectors.py`  
  Route collector output through `candidate_entries`, `candidate_keywords`, `evidence_items`, and `source_runs`.

- Modify: `backend/app/four_find.py`  
  Four-Find should write evidence and derived entries instead of behaving as a standalone destination.

- Modify: `backend/app/mvp_progress.py`  
  Opportunity progress should create evidence links to PRD hypotheses and use unified due actions.

- Modify: `backend/app/main_runtime.py`  
  Replace scattered periodic execution with unified automation cycle entrypoint.

### Frontend Files

- Modify: `frontend/components/Nav.tsx`  
  Four top-level modules: Opportunity Discovery, Evidence System, Opportunity Hunter, System Maintenance.

- Create: `frontend/components/ContextActions.tsx`  
  Shared context-aware action buttons. Each page chooses 1-2 primary actions.

- Create: `frontend/components/EvidenceTimeline.tsx`  
  Timeline component for evidence items and their service relationships.

- Create: `frontend/components/ScoreHistory.tsx`  
  Shows keyword weight events and opportunity score events.

- Create: `frontend/app/discovery/overview/page.tsx`
- Create: `frontend/app/discovery/entries/page.tsx`
- Create: `frontend/app/discovery/candidate-keywords/page.tsx`
- Modify: `frontend/app/keywords/page.tsx`
- Modify: `frontend/app/keywords/[id]/page.tsx`

- Create: `frontend/app/evidence/page.tsx`
- Create: `frontend/app/evidence/tasks/page.tsx`
- Create: `frontend/app/evidence/timeline/page.tsx`
- Create: `frontend/app/evidence/watch/page.tsx`
- Create: `frontend/app/evidence/derived/page.tsx`
- Create: `frontend/app/evidence/repairs/page.tsx`

- Modify: `frontend/app/hunter/opportunities/page.tsx`
- Modify: `frontend/components/OpportunityCard.tsx`
- Modify: `frontend/components/ProgressPage.tsx`

- Create: `frontend/app/settings/boundaries/page.tsx`
- Create: `frontend/app/settings/automation-cycle/page.tsx`
- Create: `frontend/app/settings/source-budget/page.tsx`

- Modify: `frontend/lib/api.ts`
- Modify: `frontend/types/api.d.ts`

### Test Files

- Create: `backend/tests/test_evidence_system.py`
- Create: `backend/tests/test_scoring_system.py`
- Create: `backend/tests/test_automation_cycle.py`
- Create: `backend/tests/test_action_requests.py`

Use Python standard library `unittest`. Do not add test dependencies unless user approves.

---

## Chunk 1: Data Foundation

### Task 1: Add Database Models

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/tests/test_evidence_system.py`

- [ ] **Step 1: Add model tests for objective evidence and service links**

Create `backend/tests/test_evidence_system.py`:

```python
import unittest
from datetime import datetime

from app import models


class EvidenceModelTests(unittest.TestCase):
    def test_evidence_item_has_no_scoring_fields(self):
        columns = set(models.EvidenceItem.__table__.columns.keys())
        self.assertIn("url", columns)
        self.assertIn("title", columns)
        self.assertIn("summary", columns)
        self.assertIn("confidence", columns)
        self.assertNotIn("score_delta", columns)
        self.assertNotIn("verdict", columns)

    def test_evidence_link_points_to_service_target(self):
        columns = set(models.EvidenceLink.__table__.columns.keys())
        self.assertIn("evidence_id", columns)
        self.assertIn("target_type", columns)
        self.assertIn("target_id", columns)
        self.assertIn("relation_type", columns)
        self.assertIn("relation_reason", columns)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_evidence_system -v
```

Expected: FAIL because `EvidenceItem` and `EvidenceLink` do not exist.

- [ ] **Step 3: Add SQLAlchemy models**

Add to `backend/app/models.py`:

```python
class CandidateEntry(Base):
    __tablename__ = "candidate_entries"
    __table_args__ = (UniqueConstraint("entry_type", "name", "source", "source_url", name="uq_candidate_entry_source"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_type: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    source: Mapped[str] = mapped_column(String(100), index=True, default="")
    source_role: Mapped[str] = mapped_column(String(40), index=True, default="demand")
    source_url: Mapped[str] = mapped_column(Text, default="")
    raw_context_json: Mapped[str] = mapped_column(Text, default="{}")
    trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    maturity_type: Mapped[str] = mapped_column(String(40), default="unknown")
    status: Mapped[str] = mapped_column(String(40), index=True, default="new")
    priority: Mapped[float] = mapped_column(Float, default=0.0)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (UniqueConstraint("content_hash", name="uq_evidence_content_hash"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(80), index=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True, default="")
    url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    raw_excerpt: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    content_hash: Mapped[str] = mapped_column(String(120), index=True)
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    __table_args__ = (UniqueConstraint("evidence_id", "target_type", "target_id", "relation_type", name="uq_evidence_link_target"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence_items.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(60), index=True)
    target_id: Mapped[str] = mapped_column(String(80), index=True)
    relation_type: Mapped[str] = mapped_column(String(80), index=True)
    relation_reason: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(60), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Also add `SourceRun`, `WatchTarget`, `ActionRequest`, `ActionEvent`, `KeywordWeightEvent`, and `OpportunityScoreEvent` using the same style. Keep fields nullable/defaulted for migration safety.

- [ ] **Step 4: Run tests**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_evidence_system -v
.\.venv\Scripts\python.exe -m compileall app
```

Expected: PASS and compile succeeds.

### Task 2: Add Alembic Migration

**Files:**
- Create: `backend/alembic/versions/0002_discovery_evidence_system.py`

- [ ] **Step 1: Write migration**

Create all new tables from Task 1. Use `op.create_table` and `op.create_index`. Avoid destructive changes to existing tables.

- [ ] **Step 2: Run migration on local data copy**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
$env:DEMAND_HUNTER_DATA_DIR="D:\Projects\damand-hunter\local-data\vps-20260611-024644"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Expected: migration completes. If the local data copy is locked by a running backend, stop local port `8100` first.

- [ ] **Step 3: Commit**

```powershell
git add backend/app/models.py backend/alembic/versions/0002_discovery_evidence_system.py backend/tests/test_evidence_system.py
git commit -m "feat: add discovery evidence data model"
```

---

## Chunk 2: Candidate Entries and Split Scoring

### Task 3: Candidate Entry Service

**Files:**
- Create: `backend/app/discovery_entries.py`
- Create: `backend/app/api/v1/endpoints/entries.py`
- Modify: `backend/app/api/v1/api.py`
- Create: `backend/tests/test_scoring_system.py`

- [ ] **Step 1: Write tests for entry routing**

Create tests that assert:

- `search_keyword` routes to demand scoring.
- `trend_entity`, `github_repo`, `game`, and `platform_update` route to trend scoring.
- evidence-derived words are inserted as `candidate_entries`, not directly into `keywords`.

- [ ] **Step 2: Implement entry upsert and routing**

In `backend/app/discovery_entries.py`, create:

```python
def upsert_candidate_entry(db, entry_type, name, source="", source_role="", source_url="", raw_context=None, priority=0.0):
    ...

def route_entry_next_action(entry):
    if entry.entry_type == "search_keyword":
        return "score_demand_keyword"
    if entry.entry_type in {"trend_entity", "github_repo", "game", "tool_name", "feature", "platform_update"}:
        return "score_trend_entity"
    if entry.entry_type == "domain":
        return "create_evidence_task"
    return "needs_review"
```

- [ ] **Step 3: Add entries API**

Endpoints:

```text
GET  /api/entries
POST /api/entries
POST /api/entries/{id}/push
GET  /api/entries/{id}/timeline
```

- [ ] **Step 4: Register router**

Modify `backend/app/api/v1/api.py` to include `entries.router`.

- [ ] **Step 5: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_scoring_system -v
.\.venv\Scripts\python.exe -m compileall app
```

### Task 4: Demand and Trend Scoring

**Files:**
- Create: `backend/app/scoring_system.py`
- Modify: `backend/app/models.py`
- Create: `backend/tests/test_scoring_system.py`

- [ ] **Step 1: Write scoring tests**

Tests:

- mature demand score includes demand clarity, commercial intent, SERP gap, weak competitor, MVP, monetization.
- trend entity score includes growth, problem density, ecosystem gap, toolability, translation potential.
- trend entity cannot be promoted directly to `keywords`.
- trend-derived candidate keyword must pass demand scoring before promotion.

- [ ] **Step 2: Implement pure scoring helpers**

In `backend/app/scoring_system.py`:

```python
def score_demand_keyword(keyword: str, evidence: list[dict] | None = None) -> dict:
    return {
        "score": ...,
        "breakdown": {
            "demand_clarity": ...,
            "commercial_intent": ...,
            "serp_gap": ...,
            "weak_competition": ...,
            "mvp_fit": ...,
            "monetization": ...,
        },
        "quality_gate": "pass" or "watch" or "reject",
    }

def score_trend_entity(name: str, context: dict | None = None) -> dict:
    return {
        "score": ...,
        "breakdown": {
            "growth": ...,
            "problem_density": ...,
            "ecosystem_gap": ...,
            "toolability": ...,
            "translation_potential": ...,
        },
        "next_action": "translate" or "watch" or "reject",
    }
```

- [ ] **Step 3: Record events**

When keyword weights change, create `KeywordWeightEvent`. When opportunities are rescored, create `OpportunityScoreEvent`.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_scoring_system -v
.\.venv\Scripts\python.exe -m compileall app
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/discovery_entries.py backend/app/scoring_system.py backend/app/api/v1/endpoints/entries.py backend/app/api/v1/api.py backend/tests/test_scoring_system.py
git commit -m "feat: add candidate entries and split scoring"
```

---

## Chunk 3: Objective Evidence System

### Task 5: Evidence Service and Timeline

**Files:**
- Create: `backend/app/evidence_system.py`
- Create: `backend/app/api/v1/endpoints/evidence.py`
- Modify: `backend/app/api/v1/api.py`
- Modify: `backend/tests/test_evidence_system.py`

- [ ] **Step 1: Write tests for objective evidence**

Tests:

- inserting same URL/title/excerpt dedupes by content hash.
- one evidence item can link to multiple service targets.
- evidence timeline for a keyword includes only links targeting that keyword.
- evidence item does not mutate opportunity verdict.

- [ ] **Step 2: Implement evidence capture**

In `backend/app/evidence_system.py`:

```python
def create_evidence_item(db, source_type, source_name, url, title, summary, raw_excerpt="", raw_json=None, confidence=0.0):
    ...

def link_evidence(db, evidence_id, target_type, target_id, relation_type, relation_reason="", created_by="system"):
    ...

def timeline_for_target(db, target_type, target_id, limit=100):
    ...
```

- [ ] **Step 3: Implement derived entry backflow**

Add:

```python
def create_derived_entry_from_evidence(db, evidence_id, entry_type, name, relation_reason):
    ...
```

It must write to `candidate_entries`, not `keywords`.

- [ ] **Step 4: Add evidence APIs**

Endpoints:

```text
GET  /api/evidence
POST /api/evidence
POST /api/evidence/{id}/links
GET  /api/evidence/targets/{target_type}/{target_id}/timeline
POST /api/evidence/{id}/derived-entry
GET  /api/evidence/derived
```

- [ ] **Step 5: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_evidence_system -v
.\.venv\Scripts\python.exe -m compileall app
```

### Task 6: Integrate Collectors and Four-Find with Evidence

**Files:**
- Modify: `backend/app/collectors.py`
- Modify: `backend/app/four_find.py`
- Modify: `backend/app/api/v1/endpoints/collectors.py`
- Modify: `backend/app/api/v1/endpoints/discovery.py`

- [ ] **Step 1: Write integration tests around service functions**

Use `unittest` to verify:

- sitemap result can create objective evidence.
- sitemap result can create derived entries.
- Four-Find expansion creates candidate keyword or evidence link, not direct final opportunity state.

- [ ] **Step 2: Add evidence writes in collector outputs**

For sitemap/domain/alternatives/source radar:

- write `SourceRun`;
- write `EvidenceItem` for objective page/source facts;
- link evidence to current target;
- create derived entries when title/path suggests new opportunity words.

- [ ] **Step 3: Add Four-Find evidence role**

Four-Find should produce:

```text
evidence_items
evidence_links
candidate_entries / candidate_keywords
source_runs
```

It must not be presented as a standalone business workflow.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest discover tests -v
.\.venv\Scripts\python.exe -m compileall app
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/evidence_system.py backend/app/api/v1/endpoints/evidence.py backend/app/api/v1/api.py backend/app/collectors.py backend/app/four_find.py backend/tests/test_evidence_system.py
git commit -m "feat: add objective evidence system"
```

---

## Chunk 4: Unified Automation Cycle

### Task 7: Automation Cycle Service

**Files:**
- Create: `backend/app/automation_cycle.py`
- Create: `backend/app/api/v1/endpoints/automation_cycle.py`
- Modify: `backend/app/main_runtime.py`
- Modify: `backend/app/api/v1/api.py`
- Create: `backend/tests/test_automation_cycle.py`

- [ ] **Step 1: Write tests**

Tests:

- collector due actions and evidence due actions are collected into one list.
- priority sorting prefers high-value due items.
- object has `next_due_at`, but no per-object timer is created.
- one cycle writes a `RunHistory(kind="automation_cycle")`.

- [ ] **Step 2: Implement due action collection**

In `backend/app/automation_cycle.py`:

```python
def collect_due_actions(db, now=None, limit=200) -> list[dict]:
    ...

def execute_action(db, action: dict) -> dict:
    ...

def run_automation_cycle(db, max_seconds=300, budget=None) -> dict:
    ...
```

Budget shape:

```python
{
    "discovery": 30,
    "trend": 20,
    "evidence": 50,
    "monitor": 40,
    "scoring": 50,
    "progress": 20,
}
```

- [ ] **Step 3: Replace runtime loop entry**

Modify `backend/app/main_runtime.py` so scheduled work calls `run_automation_cycle`, not many separate loops.

- [ ] **Step 4: Add API**

Endpoints:

```text
POST /api/automation-cycle/run
GET  /api/automation-cycle/due
GET  /api/automation-cycle/runs
```

- [ ] **Step 5: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_automation_cycle -v
.\.venv\Scripts\python.exe -m compileall app
```

- [ ] **Step 6: Commit**

```powershell
git add backend/app/automation_cycle.py backend/app/main_runtime.py backend/app/api/v1/endpoints/automation_cycle.py backend/app/api/v1/api.py backend/tests/test_automation_cycle.py
git commit -m "feat: add unified automation cycle"
```

---

## Chunk 5: Context-Aware Manual Actions

### Task 8: Action Request Service

**Files:**
- Create: `backend/app/action_requests.py`
- Modify: `backend/app/api/v1/endpoints/automation_cycle.py`
- Create: `backend/tests/test_action_requests.py`

- [ ] **Step 1: Write tests**

Tests:

- keyword page `recalculate` maps to keyword gate/weight action.
- opportunity page `recalculate` maps to opportunity rescore.
- evidence page `repair` appears only for abnormal evidence/task states.
- high-risk actions require confirmation.

- [ ] **Step 2: Implement action request creation**

In `backend/app/action_requests.py`:

```python
def create_action_request(db, action_type, target_type, target_id, requested_by="user", reason="", confirm=False):
    ...

def risk_for_action(action_type, target_type):
    ...

def execute_action_request(db, request_id, confirm=False):
    ...
```

Risk classes:

```text
low: run, recalculate, verify, add_watch_target
medium: promote, pause, update_gate, update_prd
high: adopt, block, delete, permanent_block, cleanup, confirm_mvp
```

- [ ] **Step 3: Add API endpoints**

Endpoints:

```text
POST /api/actions
POST /api/actions/{id}/execute
GET  /api/actions
```

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest tests.test_action_requests -v
.\.venv\Scripts\python.exe -m compileall app
```

- [ ] **Step 5: Commit**

```powershell
git add backend/app/action_requests.py backend/app/api/v1/endpoints/automation_cycle.py backend/tests/test_action_requests.py
git commit -m "feat: add context aware action requests"
```

---

## Chunk 6: Frontend Information Architecture

### Task 9: Navigation and Route Skeletons

**Files:**
- Modify: `frontend/components/Nav.tsx`
- Create: `frontend/app/discovery/overview/page.tsx`
- Create: `frontend/app/discovery/entries/page.tsx`
- Create: `frontend/app/discovery/candidate-keywords/page.tsx`
- Create: `frontend/app/evidence/page.tsx`
- Create: `frontend/app/evidence/tasks/page.tsx`
- Create: `frontend/app/evidence/timeline/page.tsx`
- Create: `frontend/app/evidence/watch/page.tsx`
- Create: `frontend/app/evidence/derived/page.tsx`
- Create: `frontend/app/evidence/repairs/page.tsx`

- [ ] **Step 1: Update nav**

Top-level groups:

```text
机会发现
证据系统
机会猎手
系统维护
```

Do not show Advanced as a primary business module.

- [ ] **Step 2: Add skeleton pages**

Each skeleton must:

- call the relevant API if available;
- show empty state;
- avoid marketing/hero layout;
- use existing `panel/card/btn/badge/input` style conventions.

- [ ] **Step 3: Verify build**

Run:

```powershell
cd D:\Projects\damand-hunter\frontend
npm run build
```

Expected: build succeeds.

### Task 10: Shared Timeline and Context Actions

**Files:**
- Create: `frontend/components/EvidenceTimeline.tsx`
- Create: `frontend/components/ScoreHistory.tsx`
- Create: `frontend/components/ContextActions.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/types/api.d.ts`

- [ ] **Step 1: Add API client methods**

Add methods for:

```text
entries list/detail/push
evidence list/timeline/link/derived
automation-cycle run/due/runs
actions create/execute/list
```

- [ ] **Step 2: Implement timeline component**

`EvidenceTimeline` props:

```ts
type EvidenceTimelineProps = {
  targetType: string
  targetId: string | number
}
```

It should show objective evidence and service relation reason. It should not describe evidence as inherently "good" or "bad".

- [ ] **Step 3: Implement context actions**

Buttons are page-specific, not globally uniform. Supported visible labels:

```text
手动抓取
推送到候选词
重新计算
补证据
重新验证
修正关联
推送到关键词库
推送到机会推进
上传 / 更新 PRD
运行一轮
修复异常
```

Each page should display only 1-2 primary buttons.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\frontend
npm run build
```

- [ ] **Step 5: Commit**

```powershell
git add frontend/components/Nav.tsx frontend/app/discovery frontend/app/evidence frontend/components/EvidenceTimeline.tsx frontend/components/ScoreHistory.tsx frontend/components/ContextActions.tsx frontend/lib/api.ts frontend/types/api.d.ts
git commit -m "feat: add discovery evidence navigation"
```

---

## Chunk 7: Page Integrations

### Task 11: Discovery and Keywords Pages

**Files:**
- Modify: `frontend/app/discovery/entries/page.tsx`
- Modify: `frontend/app/discovery/candidate-keywords/page.tsx`
- Modify: `frontend/app/keywords/page.tsx`
- Modify: `frontend/app/keywords/[id]/page.tsx`

- [ ] **Step 1: Candidate entries page**

Show:

- entry type;
- source;
- source role;
- status;
- trend score;
- next due;
- primary buttons: `手动抓取`, `推送到候选词`.

- [ ] **Step 2: Candidate keywords page**

Show:

- keyword;
- source;
- maturity type;
- evidence status;
- score breakdown;
- gate status;
- primary buttons: `重新计算`, `补证据`.

- [ ] **Step 3: Keyword detail page**

Show:

- evidence timeline;
- keyword weight events;
- source contribution;
- primary buttons: `重新计算`, `推送到关键词库` when applicable.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\frontend
npm run build
```

### Task 12: Evidence Pages

**Files:**
- Modify: `frontend/app/evidence/page.tsx`
- Modify: `frontend/app/evidence/tasks/page.tsx`
- Modify: `frontend/app/evidence/timeline/page.tsx`
- Modify: `frontend/app/evidence/watch/page.tsx`
- Modify: `frontend/app/evidence/derived/page.tsx`
- Modify: `frontend/app/evidence/repairs/page.tsx`

- [ ] **Step 1: Evidence overview**

Show:

- evidence item count;
- linked target count;
- derived entry count;
- failed task count;
- source run summary.

- [ ] **Step 2: Evidence timeline**

Show objective evidence first, then "服务对象" list.

- [ ] **Step 3: Watch targets**

Show:

- target type;
- next due;
- last run;
- last derived entries;
- primary buttons: `重新验证`, `修复异常` only when abnormal.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\frontend
npm run build
```

### Task 13: Opportunities and Progress

**Files:**
- Modify: `frontend/app/hunter/opportunities/page.tsx`
- Modify: `frontend/components/OpportunityCard.tsx`
- Modify: `frontend/components/ProgressPage.tsx`
- Modify: `backend/app/mvp_progress.py`

- [ ] **Step 1: Opportunity card timeline**

Show:

- evidence timeline for the opportunity;
- score history;
- current score breakdown;
- primary buttons: `重新计算`, `补证据`, or `推送到机会推进` depending on state.

- [ ] **Step 2: Progress page timeline**

Show:

- PRD hypothesis evidence;
- competitor watch evidence;
- pricing/MVP/SEO evidence;
- primary buttons: `上传 / 更新 PRD`, `重新验证`.

- [ ] **Step 3: Backend progress integration**

Modify `backend/app/mvp_progress.py` to create evidence links for PRD hypotheses and tracked competitors.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m compileall app
cd ..\frontend
npm run build
```

- [ ] **Step 5: Commit**

```powershell
git add frontend/app/discovery frontend/app/evidence frontend/app/keywords frontend/app/hunter frontend/components backend/app/mvp_progress.py
git commit -m "feat: wire evidence timelines into pages"
```

---

## Chunk 8: Settings, Safety, and End-to-End Verification

### Task 14: Settings Pages

**Files:**
- Create: `frontend/app/settings/boundaries/page.tsx`
- Create: `frontend/app/settings/automation-cycle/page.tsx`
- Create: `frontend/app/settings/source-budget/page.tsx`
- Modify: `frontend/app/settings/page.tsx`
- Modify: `backend/app/api/v1/endpoints/settings.py`

- [ ] **Step 1: Boundaries and preferences page**

Settings:

```text
blocked categories
opportunity preferences
high-risk action policy
```

- [ ] **Step 2: Automation cycle page**

Settings:

```text
global interval
max run seconds
per-cycle budgets
source enable flags
repair behavior
```

- [ ] **Step 3: Source budget page**

Show source ROI and editable conservative budgets.

- [ ] **Step 4: Verify**

Run:

```powershell
cd D:\Projects\damand-hunter\frontend
npm run build
```

### Task 15: End-to-End Local Smoke

**Files:**
- Modify as needed only if smoke reveals bugs.

- [ ] **Step 1: Start local app**

Run:

```powershell
cd D:\Projects\damand-hunter
.\deploy-local.bat 3100 8100
```

- [ ] **Step 2: Backend health**

Run:

```powershell
Invoke-RestMethod http://localhost:8100/api/health
```

Expected: healthy response.

- [ ] **Step 3: API smoke**

Run:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3100/discovery/overview
Invoke-WebRequest -UseBasicParsing http://localhost:3100/evidence
Invoke-WebRequest -UseBasicParsing http://localhost:3100/settings/automation-cycle
```

Expected: HTTP 200 for all.

- [ ] **Step 4: Full verification**

Run:

```powershell
cd D:\Projects\damand-hunter\backend
.\.venv\Scripts\python.exe -m unittest discover tests -v
.\.venv\Scripts\python.exe -m compileall app
cd ..\frontend
npm run build
```

- [ ] **Step 5: Commit**

```powershell
git add backend frontend docs
git commit -m "feat: complete discovery evidence refactor"
```

---

## Execution Notes

- Do not delete or migrate production data without explicit user approval.
- Use local copied DB only for development verification.
- Keep evidence objective. Do not write score deltas into `evidence_items`.
- Do not let trend entities enter `keywords` directly.
- Do not add per-project timers in V1.
- Use one unified automation cycle; future dedicated cycles must be introduced only after runtime evidence proves the need.
- Keep page buttons contextual. Each page should show 1-2 primary actions; put low-frequency and high-risk actions behind detail/More flows.

## Ready Criteria

The refactor is ready when the app can answer:

- Which evidence serves this keyword/opportunity/PRD hypothesis?
- Which evidence produced a derived entry?
- Why did a keyword weight change?
- Why did an opportunity score change?
- Which due actions ran in the latest automation cycle?
- Which actions are waiting for manual confirmation?
- Which source contributed effective entries, evidence, keywords, and opportunities?

