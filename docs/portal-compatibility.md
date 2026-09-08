# Phase 9: Real-Portal Integration & Compatibility Hardening

## Overview
Phase 9 provides the **Real-Portal Integration & Compatibility Hardening Layer** for the Agentic Job Application Platform. It shifts the platform from testing solely against simplified mock fixtures to operating against real-world ATS portals (Greenhouse, Lever, Ashby, and Generic ATS) while maintaining the absolute safety invariant:

> **NO APPROVAL = NO SUBMISSION**

The Phase 8 human approval and version-binding boundary is preserved intact.

---

## 1. Architecture

The portal compatibility layer is located in `backend/app/services/portal/`:

```text
backend/app/services/portal/
├── __init__.py               # Public package exports
├── models.py                 # PortalCapabilities, FormStepInfo, PortalExecutionError, RetryPolicy, PortalDiagnostics, PortalConfig
├── capabilities.py           # Explicit capability matrices for Greenhouse, Lever, Ashby, Generic ATS
├── config.py                 # Declarative selectors, domain patterns, field aliases, confirmation rules
├── registry.py               # PortalRegistry singleton resolving URLs to appropriate adapters
├── compatibility.py          # CompatibilityChecker validating form requirements against adapter capabilities
├── diagnostics.py            # PortalDiagnosticsCollector capturing sanitized execution telemetry
└── adapters/
    ├── __init__.py           # Package exports
    ├── base.py               # Abstract PortalAdapter base class
    ├── greenhouse.py         # Dedicated Greenhouse ATS adapter
    ├── lever.py              # Dedicated Lever ATS adapter
    ├── ashby.py              # Dedicated Ashby ATS adapter
    └── generic_ats.py        # Conservative Generic ATS fallback adapter
```

---

## 2. Portal Adapters & Capability Matrix

| Feature | Greenhouse | Lever | Ashby | Generic ATS |
| :--- | :--- | :--- | :--- | :--- |
| **Multi-Step Forms** | Yes | No (Single page sections) | Yes | Yes (Conservative) |
| **Resume Upload** | Yes (`.pdf`, `.docx`) | Yes (`.pdf`, `.docx`) | Yes (`.pdf`, `.docx`) | Yes (`.pdf`, `.docx`) |
| **Cover Letter** | Yes | Yes | Yes | Yes |
| **Custom Questions** | Yes | Yes | Yes | Yes |
| **Requires Login** | No | No | No | Detected on demand |
| **Known Confirmation Patterns** | Yes | Yes | Yes | Fallback Heuristics |

---

## 3. Strict Safety & Security Invariants

### 1. Zero Bypass Policy
- **No CAPTCHA / Anti-Bot Bypass**: If CAPTCHA, reCAPTCHA, hCaptcha, Cloudflare Turnstile, or bot verification is detected, execution pauses immediately and transitions to `REQUIRES_USER_ACTION`. The agent never attempts to solve or bypass challenges.
- **No OTP / 2FA / Authentication Bypass**: If multi-factor authentication, email/SMS codes, or login credentials are required, execution pauses immediately.

### 2. Zero Credential Persistence
- Passwords, OTPs, session cookies, authorization headers, and API secrets are **NEVER** persisted in database records, logs, screenshots, audit metadata, or debug output.
- All query parameters in diagnostics URLs (`?token=...`, `?password=...`) are stripped by `PortalDiagnosticsCollector.sanitize_url`.

### 3. Safe Retry Policy
- **Allowed**: Transient network timeouts, temporary navigation errors, and page load timeouts for read operations.
- **Strictly Prohibited**: Final submission clicks, ambiguous submissions, CAPTCHA challenges, OTPs, or authentication forms are **NEVER** retried automatically.

### 4. Ambiguous Submissions
- If the submit button is clicked but confirmation cannot be conclusively proven from URLs or DOM banners, the system transitions to `REQUIRES_USER_ACTION` with `AMBIGUOUS_POST_SUBMISSION` and **NEVER** clicks submit again.

---

## 4. Manual Real-Portal Validation Tooling

Developers can inspect real-world job postings interactively without bypassing approval boundaries:

```bash
# Headless inspection
python scripts/validate_portal.py "https://boards.greenhouse.io/acme/jobs/12345" --headless

# Interactive headed session
python scripts/validate_portal.py "https://boards.greenhouse.io/acme/jobs/12345"
```

The tool:
1. Detects the matching portal adapter.
2. Navigates to the application URL.
3. Evaluates authentication and challenge status.
4. Discovers and logs all visible form fields safely.
5. Captures sanitized diagnostics.
6. Strictly terminates without executing final submission.

---

## 5. Verification & Testing

The full backend suite verifies all 200 unit and integration tests:
```bash
PYTHONPATH=. .venv/bin/pytest
# Result: 200 passed, 8 warnings in 38s
```
Frontend production build:
```bash
cd frontend && npm run build
# Result: Compiled successfully, TypeScript passed, static pages generated cleanly
```
