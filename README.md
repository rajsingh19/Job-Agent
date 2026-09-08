# Job Application Agent (MVP)

A production-oriented, **Human-In-The-Loop** AI platform for autonomous job discovery, resume matching, application drafting, and submission tracking.

## Product Principle: Human-In-The-Loop
The agent automates discovery, semantic ranking, and field preparation, but **final submission strictly requires explicit user approval**. The system never silently submits applications and never bypasses anti-bot/CAPTCHA/OTP challenges.

---

## Current Status: Phase 8 Complete

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

### Phase 7 Deliverables:
- **Playwright Browser & Session Managers (`BrowserManager`, `SessionManager`)**: Headless/headed Chromium lifecycle management, dynamic asyncio event loop rebinding, and multi-tenant session isolation (`0o600` permissions, zero cookie leakage).
- **Security & Challenge Detection (`AuthDetector`, `ChallengeDetector`)**: Scans for login redirects, CAPTCHA (Turnstile/reCAPTCHA), Cloudflare bot checks, OTP, and 2FA. Strictly pauses execution with `USER_ACTION_REQUIRED` and zero bypass attempts.
- **Form Inspection & Parsing (`PageInspector`, `FormParser`)**: Safe DOM inspection extracting normalized inputs, textareas, selects, and distinguishing step navigation buttons from submit controls.
- **Phase 6 Draft Integration & Sensitive Guard (`FieldDetector`)**: Maps verified draft fields to DOM inputs. Sensitive questions (sponsorship, legal authorization, disabilities, unconfigured salary) strictly default to `REQUIRES_USER_INPUT`.
- **Safe Execution & Resume Upload (`FieldExecutor`, `ResumeUploader`)**: Executes verified inputs and uploads candidate resumes with path containment checks.
- **CRITICAL Hard Submission Guard (`SubmissionBlockedError`)**: Hard-coded service level barrier that strictly blocks clicking any final "Submit", "Apply Now", or "Finish Application" button.
- **Visual Checkpoint Capture (`ScreenshotManager`)**: Captures full-page screenshots at key milestones and embeds them into Phase 6 review packages.
- **REST Browser Automation API**:
  - `POST /api/v1/browser/sessions`
  - `GET /api/v1/browser/sessions/{session_id}`
  - `POST /api/v1/browser/applications/{application_id}/start`
  - `GET /api/v1/browser/sessions/{session_id}/form`
  - `POST /api/v1/browser/sessions/{session_id}/resume`
  - `POST /api/v1/browser/sessions/{session_id}/pause`
  - `GET /api/v1/browser/applications/{application_id}/execution`
  - `GET /api/v1/browser/applications/{application_id}/screenshots`
- **Frontend Browser Console**: Next.js App Router dashboard (`/applications/[id]/execution`) displaying real-time execution progress, detected form fields, user action prompts, and visual checkpoints.

### Phase 8 Deliverables:
- **Approval Validation & Review Versioning (`ApprovalValidator`)**: Deterministic SHA-256 version hash generation across form fields, answers, resume ID, and cover letter. Changes to draft content immediately invalidate existing approval.
- **Application Approval Service (`ApprovalService`)**: Enforces explicit human confirmation checkbox, pre-submission structural validation, generates cryptographic single-use approval tokens, records `ApplicationApproval` entries, and emits audit events.
- **Hard-Coded Backend Submission Guard (`SubmissionGuard`)**: Strict gate requiring active unexpired approval, exact review version match, concurrency locking (`asyncio.Lock`), and idempotency check blocking `AlreadySubmittedError`.
- **Browser Submitter Execution (`BrowserSubmitter`)**: Validates `SubmissionAuthorization` token before any final click action, locates portal submit buttons, captures pre-click and post-click visual checkpoints, and handles security challenge blocks.
- **Post-Submission Confirmation Detector (`SubmissionConfirmationDetector`)**: Classifies submission outcomes (`CONFIRMED`, `NOT_CONFIRMED`, `UNKNOWN`) based on URL path rules, DOM text patterns, error banner detection, and extracts confirmation reference codes.
- **Submission Orchestration Service (`SubmissionService`)**: Coordinates the transition `APPROVED` -> `SUBMITTING` -> `SUBMITTED` / `REQUIRES_USER_ACTION` / `FAILED`, persists confirmation data, and records status history.
- **Immutable Append-Only Audit Trail (`AuditService`)**: Logs all lifecycle events (`VALIDATION_PASSED`, `APPROVED`, `APPROVAL_REVOKED`, `SUBMISSION_INITIATED`, `SUBMISSION_CONFIRMED`, `SUBMISSION_FAILED`) with automatic redaction of sensitive credentials.
- **REST Human Approval & Submission API**:
  - `POST /api/v1/applications/{application_id}/approve`
  - `POST /api/v1/applications/{application_id}/revoke-approval`
  - `GET /api/v1/applications/{application_id}/approval`
  - `POST /api/v1/applications/{application_id}/submit`
  - `GET /api/v1/applications/{application_id}/submission`
  - `GET /api/v1/applications/{application_id}/audit`
- **Frontend Review & Approval Dashboard**: Next.js App Router review cockpit (`/applications/[id]/review`) displaying complete application package, field review, Q&A confidence, cover letter, checkpoint screenshots, approval checkbox, auto-pilot submission trigger, and audit trail drawer.

### Phase 9 Deliverables:
- **Portal Compatibility Architecture (`backend/app/services/portal/`)**: Modular capability model, declarative configurations, registry, and compatibility checking for Greenhouse, Lever, Ashby, and Generic ATS.
- **Multi-Step Application Progression**: Dynamic step progression with DOM stabilization (`networkidle` / `domcontentloaded`), checkpoint capture, and re-discovery without stale references.
- **Authentication & Challenge Detection Hardening**: Proactive pausing on login redirects, password fields, SSO, CAPTCHAs (Turnstile, Cloudflare, reCAPTCHA), and OTP/2FA without bypassing security challenges.
- **Resume Upload Hardening**: Multi-tenant isolation, 10MB size enforcement, allowed extension validation (`.pdf`, `.docx`), path traversal defense, and zero raw path leakage.
- **Submission Confirmation Hardening**: Multi-source confirmation detection across URLs, DOM success banners, and reference code extraction (`GH-`, `LEV-`, `ASH-`), strictly blocking automatic retries on ambiguous submissions.
- **Safe Diagnostics & Logging**: Zero credential/cookie/secret leakage, sanitized navigation history, and structured telemetry.
- **Manual Real-Portal Validation Tool (`scripts/validate_portal.py`)**: Headed/headless developer inspection tool operating strictly within the Phase 8 approval boundary.
- **REST Portal API**:
  - `GET /api/v1/portals`
  - `GET /api/v1/portals/{portal_id}`
  - `GET /api/v1/applications/{application_id}/portal-diagnostics`
  - `POST /api/v1/applications/{application_id}/execution/resume`
  - `POST /api/v1/applications/{application_id}/execution/pause`
- **Updated Execution Cockpit**: Extended `/applications/[id]/execution` dashboard with real portal badges, multi-step progression indicators, authentication alerts, and diagnostic drawers.

---

## Quickstart

### 1. Environment Setup
```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
playwright install chromium
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

### 5. Run Frontend Development Server
```bash
cd frontend
npm run dev
```
- Browser execution console: http://localhost:3000/applications/app_demo_001/execution
- Human approval & review dashboard: http://localhost:3000/applications/app_demo_001/review

---

## Roadmap

- [x] **Phase 1: Repository + Database + Models + Configuration**
- [x] **Phase 2: Resume / Candidate Profile System**
- [x] **Phase 3: Job Discovery (Greenhouse, Lever, Ashby, Generic Browser)**
- [x] **Phase 4: Matching Engine (Hard filters + Hybrid Semantic Ranking)**
- [x] **Phase 5: ATS Detection + Connector Architecture**
- [x] **Phase 6: Application Drafting & Grounded Answer Generation**
- [x] **Phase 7: Browser Agent (Playwright)**
- [x] **Phase 8: Human Approval & Final Application Submission**
- [x] **Phase 9: Real-Portal Integration & Compatibility Hardening**
- [ ] **Phase 10: Tracking & Metrics**
- [ ] **Phase 11: Next.js Frontend Dashboard**
- [ ] **Phase 12: Email Monitoring**
- [ ] **Phase 13: Scheduler & Rate Limiting**
- [ ] **Phase 14: End-to-End Integration Testing**
