# Phase 7: Browser Execution & Session Automation

## 1. Overview & Architectural Principles

Phase 7 introduces the **Playwright Execution Layer** for the **Job Application Agent**, transforming verified Phase 6 application drafts into prepared form sessions.

### The Inviolable Scope Invariant
> **Phase 7 prepares, navigates, and safely fills applications, but Phase 7 CAN NEVER submit an application.**
> 
> Final submission requires explicit human review and authorization, enforced by **Phase 8: Human Approval & Submission**.

---

## 2. Core Service Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│               Phase 6 Application Draft                     │
│  (Candidate Context + Form Fields + Truthful Q&A + Resume)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 BrowserExecutionService                     │
│  Coordinates session lifecycle, navigation, and execution   │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
       ▼                       ▼                       ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│BrowserManager│       │SessionManager│       │ AuthDetector │
│  Chromium    │       │Tenant Storage│       │ & Challenge  │
│  Lifecycles  │       │  Isolation   │       │  Detectors   │
└──────────────┘       └──────────────┘       └──────────────┘
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             Page Inspection & Generic Form Parser           │
│    Discovers visible inputs, selects, radios, and buttons   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        FieldDetector                        │
│    Maps DOM inputs to Phase 6 verified fields & questions   │
│   Sensitive questions strictly flag requires_user_input     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│              FieldExecutor & ResumeUploader                 │
│      Fills text, selects options, uploads valid resume      │
│   HARD GUARD: SubmissionBlockedError on any submit control  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│       Visual Checkpoints (ScreenshotManager)                │
│    Embeds checkpoints into Phase 6 ReviewPackage            │
│   Sets Application status: READY_FOR_REVIEW / USER_ACTION   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Key Components

### 3.1 Playwright BrowserManager & SessionManager
- **BrowserManager (`browser_manager.py`)**:
  - Manages headless/headed Chromium browser processes with controlled resource limits.
  - Dynamically detects and rebinds to active asyncio event loops, preventing deadlocks during async testing and multi-session workflows.
  - Safe exception-handled context cleanup.
- **SessionManager (`session_manager.py`)**:
  - Enforces strict multi-tenant isolation (`session.user_id == current_user.id`).
  - Persists authenticated browser context state to `storage/browser_sessions/{user_id}_{session_id}_state.json` with restricted permissions (`0o600`).
  - **Zero Credential Leakage**: Never logs, stores, or exposes cookies, tokens, or storage states in API responses.

### 3.2 Detection Layers (Strict Zero-Bypass Policy)
- **AuthDetector (`auth_detector.py`)**:
  - Detects login pages via URL paths (`/login`, `/signin`, `/auth`), password input presence, and landing buttons.
  - If authentication is required, halts execution and sets status to `USER_ACTION_REQUIRED` (`AUTHENTICATION_REQUIRED`).
  - Allows human-assisted login directly in the browser session without ever asking for or storing passwords.
- **ChallengeDetector (`challenge_detector.py`)**:
  - Detects CAPTCHAs (reCAPTCHA, hCaptcha, Cloudflare Turnstile), Cloudflare bot checks, OTP inputs, and 2FA prompts.
  - **Strict Anti-Bypass Rule**: Never attempts to defeat, solve, rotate fingerprints, or evade security mechanisms. Immediately signals `USER_ACTION_REQUIRED` for manual human resolution.

### 3.3 Form Inspection & Field Mapping
- **PageInspector (`page_inspector.py`) & FormParser (`form_parser.py`)**:
  - Scans visible DOM inputs, selects, textareas, and file upload fields.
  - Distinguishes intermediate navigation buttons ("Next", "Continue") from final submission controls ("Submit", "Apply Now").
- **FieldDetector (`field_detector.py`)**:
  - Maps visible fields to the Phase 6 `ApplicationDraft` using exact labels, aliases, and autocomplete tags.
  - **Sensitive Field Protection**: Work authorization, sponsorship, equal opportunity declarations, and unconfigured salary questions default to `REQUIRES_USER_INPUT` and are NEVER autofilled without explicit user confirmation.

### 3.4 Safe Execution & Submission Guard
- **ResumeUploader (`resume_uploader.py`)**:
  - Verifies candidate ownership of the Phase 6 selected resume.
  - Validates file existence on disk, allowed file formats (.pdf, .docx), and path containment within `storage/resumes` to prevent path traversal attacks.
- **FieldExecutor (`field_executor.py`)**:
  - Safely fills inputs and selects options on visible, enabled elements.
  - **Hard Submission Guard (`SubmissionBlockedError`)**: An explicit service-level barrier that inspects any target button. If keywords matching "Submit", "Submit Application", "Apply Now", or "Finish Application" are detected, raises `SubmissionBlockedError` immediately.

### 3.5 Checkpoint Screenshots & Review Integration
- **ScreenshotManager (`screenshot_manager.py`)**:
  - Captures visual checkpoints (`after_navigation`, `form_initial`, `after_safe_fill`, `user_action_required`).
  - Generates UUID filenames in `storage/screenshots/` without persisting secrets.
  - Embeds captured screenshots directly into the application's `review_package["screenshots"]`.

---

## 4. REST API Reference

Mounted under `/api/v1/browser`:

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/v1/browser/sessions` | Create an isolated browser session |
| `GET` | `/api/v1/browser/sessions/{session_id}` | Retrieve safe session metadata (no cookies/tokens) |
| `POST` | `/api/v1/browser/applications/{application_id}/start` | Start automated application preparation |
| `GET` | `/api/v1/browser/sessions/{session_id}/form` | Inspect visible form fields on active page |
| `POST` | `/api/v1/browser/sessions/{session_id}/resume` | Resume execution after user manual action |
| `POST` | `/api/v1/browser/sessions/{session_id}/pause` | Pause active browser automation |
| `GET` | `/api/v1/browser/applications/{application_id}/execution` | Retrieve live execution snapshot |
| `GET` | `/api/v1/browser/applications/{application_id}/screenshots` | List visual execution checkpoints |

---

## 5. Security & Isolation Invariants

1. **Multi-Tenant Isolation**: Users can only access, view, or control browser sessions and screenshots that belong to their account.
2. **Filesystem Safety**: Path resolution verifies that resume paths stay strictly within `storage/resumes` and session state files stay strictly within `storage/browser_sessions`.
3. **No Credential Storage**: Passwords, OTPs, and authorization tokens are never prompted for, intercepted, or persisted by the backend.
4. **No Anti-Bot Bypass**: No stealth evasion tooling or automated CAPTCHA solvers are implemented.
5. **No Final Submission in Phase 7**: The backend guarantees that Phase 7 transitions applications to `READY_FOR_REVIEW` (or `REQUIRES_USER_ACTION`), never to `SUBMITTING` or `SUBMITTED`.
