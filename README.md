# Job Application Agent (MVP)

A production-oriented, **Human-In-The-Loop** AI platform for autonomous job discovery, resume matching, application drafting, and submission tracking.

## Product Principle: Human-In-The-Loop
The agent automates discovery, semantic ranking, and field preparation, but **final submission strictly requires explicit user approval**. The system never silently submits applications and never bypasses anti-bot/CAPTCHA/OTP challenges.

---

## Current Status: Phase 6 Complete

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

### Phase 4 Deliverables:
- **Hard Constraint Engine**: Structured evaluation of candidate constraints (excluded companies, work mode, location, minimum compensation) with `UNKNOWN` constraint handling.
- **Keyword & Skill Matcher**: Canonical skill overlap detection with synonym expansion and false-positive word boundary prevention.
- **Semantic Vector Matcher**: Deterministic candidate & job representation embeddings with cosine similarity calculations.
- **Resilient Fallback Engine**: Seamless dynamic weight redistribution across keyword, role, and experience factors during external provider downtime.
- **Role & Experience Matchers**: Multi-cluster role similarity and experience level hierarchy comparison.
- **Explainability & Confidence Indicators**: Deterministic match reasoning generation with bounded quality indicator.
- **REST Matching API**: `POST /api/v1/jobs/{job_id}/match`, `POST /api/v1/jobs/match`, and `GET /api/v1/jobs/ranked`.

### Phase 5 Deliverables:
- **ATS Detection Engine (`ATSDetector`)**: Deterministic pattern matching and signal evaluation across Greenhouse, Lever, Ashby, LinkedIn, Internshala, Naukri, Shine, Wellfound, and generic enterprise ATSs with conflict resolution.
- **Connector Registry & Capabilities**: Centralized `ConnectorRegistry` with honest capability reporting (`can_submit_application=False` strictly enforced).
- **Platform Connectors**: Native implementations for `GreenhouseConnector`, `LeverConnector`, `AshbyConnector`, and `GenericBrowserConnector`.
- **Connector Routing (`ConnectorRouter`)**: Full route resolution mapping job metadata to execution parameters (`requires_browser`, `requires_login`, `requires_user_action`).
- **REST Connector API**: `POST /api/v1/jobs/{job_id}/detect-platform`, `GET /api/v1/jobs/{job_id}/application-route`, and `GET /api/v1/connectors`.

### Phase 6 Deliverables:
- **Multi-Resume Scoring & Selection (`ResumeSelector`)**: Candidate resume selection evaluated against job requirements, semantic skills, and domain keywords with score delta thresholding (`delta < 0.15` triggers user review flag).
- **Deterministic Field Mapping (`ApplicationFieldMapper`)**: Regex-driven form label mapping with strict source precedence hierarchy (`USER_INPUT` > `USER_PREFERENCE` > `CANDIDATE_PROFILE` > `RESUME` > `DERIVED` > `UNKNOWN`).
- **Rule-Based Question Classifier (`QuestionClassifier`)**: Multi-category regex classification for 12 question types (authorization, sponsorship, salary, start date, relocation, years of experience, technical skills, background check, custom subjective, etc.).
- **Grounded Answer Generator (`QuestionAnswerer`)**: Strict zero-hallucination factual answer generation. Legal, authorization, disability, and unconfigured compensation questions strictly flag `requires_user_input = True`.
- **Truthful Cover Letter Generator (`CoverLetterGenerator`)**: Grounded cover letters citing only verified candidate achievements and job requirements, with resilient fallback to `None` + review warning.
- **Pre-Flight Application Validator (`ApplicationDraftValidator`)**: Email, phone, URL format validation, missing required field detection, and anti-fabrication truthfulness verification.
- **Review Package Builder (`ReviewPackageGenerator`)**: Aggregates structured fields, answers, warnings, validation status, and empty screenshot placeholders ready for Phase 7 browser automation.
- **REST Application Draft API**:
  - `POST /api/v1/jobs/{job_id}/application-draft`
  - `GET /api/v1/applications/{application_id}/draft`
  - `POST /api/v1/applications/{application_id}/validate`
  - `GET /api/v1/applications/{application_id}/review`

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
- [x] **Phase 4: Matching Engine (Hard filters + Hybrid Semantic Ranking)**
- [x] **Phase 5: ATS Detection + Connector Architecture**
- [x] **Phase 6: Application Drafting & Grounded Answer Generation**
- [ ] **Phase 7: Browser Agent (Playwright)**
- [ ] **Phase 8: Authentication & Persistent Session Manager**
- [ ] **Phase 9: Application Approval Queue**
- [ ] **Phase 10: Tracking & Metrics**
- [ ] **Phase 11: Next.js Frontend Dashboard**
- [ ] **Phase 12: Email Monitoring**
- [ ] **Phase 13: Scheduler & Rate Limiting**
- [ ] **Phase 14: End-to-End Integration Testing**
