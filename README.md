# Job Application Agent (MVP)

A production-oriented, **Human-In-The-Loop** AI platform for autonomous job discovery, resume matching, application drafting, and submission tracking.

## Product Principle: Human-In-The-Loop
The agent automates discovery, semantic ranking, and field preparation, but **final submission strictly requires explicit user approval**. The system never silently submits applications and never bypasses anti-bot/CAPTCHA/OTP challenges.

---

## Current Status: Phase 3 Complete

### Phase 1 Deliverables:
- Repository structure, configuration engine, async SQLAlchemy ORM models, state machine, Alembic migrations, and testing suite.

### Phase 2 Deliverables:
- Resume upload API (PDF/DOCX), text extraction layer, LLM & fallback parsers, candidate profile synthesizers, and multi-tenant security.

### Phase 3 Deliverables:
- **Multi-Source Discovery Engine**: Unified discovery architecture supporting `APISource` (Greenhouse, Lever), `ATSSource` (Ashby), and `BrowserSource` (`GenericBrowserDiscovery`).
- **Failure Isolation & Resiliency**: Exponential backoff retries and bounded concurrency (`asyncio.Semaphore`); failing sources never crash the discovery run.
- **Normalization Layer**: Standardized company names, expanded abbreviations in job titles, normalized remote types (`REMOTE`, `HYBRID`, `ON_SITE`), and canonical skill extraction.
- **Deduplication Engine**: Deterministic `source_hash` generation and fuzzy cross-source deduplication.
- **Idempotent Persistence**: `JobRepository` ensuring repeated discovery runs update existing postings without duplicate database records.
- **REST Discovery API**: `POST /api/v1/jobs/discover`, `GET /api/v1/jobs`, and `GET /api/v1/jobs/{job_id}`.

---

## Quickstart

### 1. Environment Setup
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` (already pre-configured for local testing):
```bash
cp .env.example .env
```

### 3. Run Backend Tests
```bash
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -v
```

### 4. Run Development Server
```bash
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --reload --port 8000
```
Visit http://localhost:8000/docs for Swagger documentation.

---

## Roadmap

- [x] **Phase 1: Repository + Database + Models + Configuration**
- [x] **Phase 2: Resume / Candidate Profile System**
- [x] **Phase 3: Job Discovery (Greenhouse, Lever, Ashby, Generic Browser)**
- [ ] **Phase 4: Matching Engine (Hard filters + Hybrid Semantic Ranking)**
- [ ] **Phase 5: ATS Detection + Connector Architecture**
- [ ] **Phase 6: Application Drafting & Grounded Answer Generation**
- [ ] **Phase 7: Browser Agent (Playwright)**
- [ ] **Phase 8: Authentication & Persistent Session Manager**
- [ ] **Phase 9: Application Approval Queue**
- [ ] **Phase 10: Tracking & Metrics**
- [ ] **Phase 11: Next.js Frontend Dashboard**
- [ ] **Phase 12: Email Monitoring**
- [ ] **Phase 13: Scheduler & Rate Limiting**
- [ ] **Phase 14: End-to-End Integration Testing**
