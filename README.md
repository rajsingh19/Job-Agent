# Job Application Agent (MVP)

A production-oriented, **Human-In-The-Loop** AI platform for autonomous job discovery, resume matching, application drafting, and submission tracking.

## Product Principle: Human-In-The-Loop
The agent automates discovery, semantic ranking, and field preparation, but **final submission strictly requires explicit user approval**. The system never silently submits applications and never bypasses anti-bot/CAPTCHA/OTP challenges.

---

## Current Status: Phase 2 Complete

### Phase 1 Deliverables:
- Repository structure, configuration engine, async SQLAlchemy ORM models, state machine, Alembic migrations, and testing suite.

### Phase 2 Deliverables:
- **Resume Ingestion & Upload API**: Multipart upload for PDF & DOCX with MIME/extension validation, size enforcement (10MB), path traversal protection, and SHA-256 content hashing.
- **Text Extraction Layer**: Abstraction with `PDFResumeExtractor` and `DOCXResumeExtractor`. Detects scanned/image-only documents (`TEXT_EXTRACTION_REQUIRED`) and password/corrupted files (`FILE_CORRUPTED`).
- **AI / LLM Provider Abstraction**: Vendor-agnostic provider layer (`OpenAILLMProvider`, `GroqLLMProvider`, `OllamaLLMProvider`, `MockLLMProvider`).
- **Structured LLM Parser & Grounding**: `LLMResumeParser` strictly extracting verified candidate data without hallucinating experience or skills.
- **Deterministic Fallback Parser**: `FallbackResumeParser` activated on LLM unavailability, setting `low_confidence = True` and logging audit warnings.
- **Authoritative Preferences & Candidate Profile**: Independent persistence of `UserPreferences` and `ResumeProfile` joined seamlessly via `CandidateProfileService` (`GET /api/v1/profile`).
- **Structured Error Handling**: Standardized error payloads for `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`, `FILE_CORRUPTED`, `TEXT_EXTRACTION_FAILED`, `TEXT_EXTRACTION_REQUIRED`, `LLM_UNAVAILABLE`, `LLM_PARSE_FAILED`, `RESUME_NOT_FOUND`, `FORBIDDEN_RESOURCE_ACCESS`.

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
