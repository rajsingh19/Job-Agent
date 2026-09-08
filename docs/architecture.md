# Job Application Agent — Architecture & Design

## Overview

**Job Application Agent** is a production-oriented, Human-In-The-Loop system designed to autonomously discover, rank, prepare, and track job applications across APIs, ATS connectors, and browser automation while enforcing mandatory human review before any final submission.

## Core Architectural Layers

1. **Configuration & Security (`app.config`)**
   - Typed Pydantic `Settings` supporting `.env` and environment variables.
   - Provider-agnostic abstractions for AI (OpenAI, Anthropic, Groq, Ollama, Mock) and Embeddings.
   - Session isolation and credential protection.
   - Zero hardcoded secrets.

2. **Data Model & Persistence (`app.models` & `app.database`)**
   - SQLAlchemy 2.0 Async ORM with SQLite for development and PostgreSQL compatibility.
   - Append-only status history for complete audit trails.
   - Strict separation of parsed `ResumeProfile` from explicit `UserPreferences` so LLM parsing never overwrites user constraints.

3. **Lifecycle State Machine (`app.schemas.state_machine`)**
   - Formal transition rules preventing any silent submissions.
   - Mandatory transition pathway: `PENDING_REVIEW` -> `APPROVED` -> `SUBMITTING` -> `SUBMITTED`.
   - Dedicated exception handling for `REQUIRES_USER_ACTION` when anti-bot, OTP, or CAPTCHA challenges arise.

4. **Directory Structure**
```text
job_application_agent/
│
├── backend/
│   ├── app/
│   │   ├── api/             # REST API routers & versioned endpoints
│   │   ├── models/          # SQLAlchemy ORM models & enums
│   │   ├── schemas/         # Pydantic data schemas & state machine
│   │   ├── services/        # Business logic services
│   │   ├── agents/          # Autonomous agents & planners
│   │   ├── connectors/      # Platform connectors (Greenhouse, Lever, Ashby, Browser)
│   │   ├── browser/         # Playwright browser agent & session management
│   │   ├── matching/        # Hard filtering & semantic ranking engine
│   │   ├── applications/    # Application drafting & review packaging
│   │   ├── tracking/        # Status metrics & event tracking
│   │   ├── email/           # Email monitoring abstraction
│   │   ├── scheduling/      # Discovery schedulers & rate limiters
│   │   ├── config/          # Pydantic settings & environment configuration
│   │   ├── database/        # Async SQLAlchemy session management
│   │   └── main.py          # FastAPI application entrypoint
│   │
│   ├── tests/               # Pytest suite with local fixtures
│   └── migrations/          # Alembic migrations
│
├── frontend/                # Next.js TypeScript Dashboard (Phase 11)
├── storage/
│   ├── resumes/             # Uploaded resume files
│   ├── sessions/            # Isolated persistent browser sessions
│   └── screenshots/         # Review package screenshot previews
│
├── docs/                    # Architecture and developer documentation
├── .env.example             # Configuration reference
├── .gitignore               # Security and artifact ignore rules
└── README.md                # Project documentation
```
