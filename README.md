# Job Application Agent (MVP)

A production-oriented, **Human-In-The-Loop** AI platform for autonomous job discovery, resume matching, application drafting, and submission tracking.

## Product Principle: Human-In-The-Loop
The agent automates discovery, semantic ranking, and field preparation, but **final submission strictly requires explicit user approval**. The system never silently submits applications and never bypasses anti-bot/CAPTCHA/OTP challenges.

---

## Current Status: Phase 1 Complete

### Phase 1 Deliverables:
- **Repository Structure**: Modular layout separating backend, frontend, storage, migrations, and documentation.
- **Configuration Engine**: Typed Pydantic `Settings` loading from `.env` with validation, directory provisioning, and vendor-agnostic AI provider options.
- **Data Models**:
  - `User`: Base identity entity.
  - `Resume`: Uploaded resumes with content hashing and structured `ResumeProfile` JSON.
  - `UserPreference`: Explicit user filters (target roles, locations, remote preference, minimum stipend, excluded companies).
  - `JobPosting`: Normalized job posting model with ATS provider detection and source hashing for deduplication.
  - `Application`: Application entity tracking matches, drafted fields, generated answers, warnings, and review packages.
  - `ApplicationStatusHistory`: Append-only audit trail recording every state transition with actor and reason.
- **State Machine**: Enforced application lifecycle (`DISCOVERED` -> `MATCHED` -> `DRAFTING` -> `PENDING_REVIEW` -> `APPROVED` -> `SUBMITTING` -> `SUBMITTED`, etc.) with strict programmatic blocks against unapproved submissions.
- **FastAPI Skeleton**: Asynchronous FastAPI app with dependency injection, CORS middleware, lifespan events, and `/api/v1/system/health` check.
- **Alembic Migrations**: Async database migration setup for SQLite and PostgreSQL.
- **Testing Suite**: 100% passing pytest suite covering configuration, models, schemas, database cascade integrity, state machine transitions, and API endpoints.

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
- [ ] **Phase 2: Resume / Candidate Profile System**
- [ ] **Phase 3: Job Discovery (Greenhouse, Lever, Ashby, Generic Browser)**
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
