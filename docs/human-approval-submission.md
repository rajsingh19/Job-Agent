# Phase 8: Human Approval & Final Application Submission

## 1. Overview & Architectural Principles

Phase 8 introduces the **Human Approval & Execution Boundary** for the **Job Application Agent**, establishing the final bridge between prepared candidate application packages (Phase 7 `PENDING_REVIEW` / `READY_FOR_REVIEW`) and actual live portal submission.

### The Inviolable Core Invariant
> **NO APPROVAL = NO SUBMISSION**
>
> 1. **Backend Enforced**: A frontend button alone is never trusted. All approval, versioning, cryptographic authorization, and validation checks are strictly verified and enforced at the backend service layer before any portal submission action can occur.
> 2. **Version-Bound Cryptographic Approvals**: Candidate approval is bound to a deterministic SHA-256 hash of the exact application state. Any modification to draft fields, custom question answers, selected resume, or cover letter invalidates existing approval.
> 3. **Single-Use Cryptographic Tokens**: `BrowserSubmitter` executes only when presented with a valid, unexpired `SubmissionAuthorization` token signed for the target application and matching version hash.
> 4. **Strict Idempotency & Anti-Double-Submit**: Double submissions are strictly blocked via `AlreadySubmittedError`, and concurrent submissions on the same application are serialized and locked with `ConcurrentSubmissionError`.
> 5. **Immutable Audit Trail**: Every approval, revocation, submission attempt, and confirmation signal is recorded in an append-only, tenant-isolated audit log with sensitive information automatically redacted.

---

## 2. Component Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                 Candidate Review Interface                  │
│       (Next.js Dashboard + Field Review + Checkpoints)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                Candidate Explicit Approval
               (POST /applications/{id}/approve)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       ApprovalService                       │
│  - Pre-submission validation (resume, emails, URLs, inputs) │
│  - Deterministic SHA-256 version hash generation            │
│  - Issues single-use cryptographic approval_token           │
│  - Records ApplicationApproval & emits Audit Event          │
│  - Advances Application status: PENDING_REVIEW -> APPROVED  │
└──────────────────────────────┬──────────────────────────────┘
                               │
              Autonomous / Candidate Submission
               (POST /applications/{id}/submit)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                       SubmissionGuard                       │
│  - Concurrency Lock (prevents parallel submissions)         │
│  - Verifies status == APPROVED                              │
│  - Re-computes review hash & verifies approval token        │
│  - Checks idempotency (blocks AlreadySubmittedError)        │
│  - Emits SubmissionAuthorization token                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      BrowserSubmitter                       │
│  - Validates SubmissionAuthorization & application ID       │
│  - Identifies final submission controls                     │
│  - Captures pre-submission screenshot checkpoint            │
│  - Executes final click / submit on Playwright page         │
│  - Captures post-submission screenshot checkpoint           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                SubmissionConfirmationDetector               │
│  - Evaluates URL patterns (/thank-you, /confirmation, etc.) │
│  - Scans DOM text for success & error banners               │
│  - Extracts confirmation / reference codes                  │
│  - Classifies: CONFIRMED, NOT_CONFIRMED, or UNKNOWN         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                      SubmissionService                      │
│  - Updates Application: SUBMITTING -> SUBMITTED or ACTION   │
│  - Persists submitted_at timestamp & confirmation reference │
│  - Logs immutable audit entries (AuditService)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Review Version Hashing & Tamper Detection

`ApprovalValidator.calculate_review_version_hash(draft)` creates a canonical, deterministic SHA-256 digest of:
- `fields`: Sorted list of field IDs, normalized values, and field types.
- `custom_questions`: Sorted list of question IDs, answers, and prompt texts.
- `resume_id`: Unique identifier of the attached resume.
- `cover_letter`: Content of the generated cover letter.

If any field, answer, resume selection, or cover letter content is modified after candidate approval, the re-computed hash diverges, causing `SubmissionGuard` to reject submission with `ApprovalExpiredError`.

---

## 4. State Machine Transitions

| From Status | Destination Status | Allowed Trigger | Invariant Check |
|---|---|---|---|
| `PENDING_REVIEW` | `APPROVED` | `POST /applications/{id}/approve` | Pre-submission validation must pass; explicit confirmation checkbox must be true. |
| `APPROVED` | `PENDING_REVIEW` | `POST /applications/{id}/revoke-approval` | User or system revokes approval; marks active approval revoked. |
| `APPROVED` | `SUBMITTING` | `POST /applications/{id}/submit` | SubmissionGuard verifies active approval token & hash match. |
| `SUBMITTING` | `SUBMITTED` | `SubmissionService.execute_submission` | Confirmation detector confirms success via URL or text pattern. |
| `SUBMITTING` | `REQUIRES_USER_ACTION` | `SubmissionService.execute_submission` | Bot challenge (CAPTCHA), 2FA detected, or ambiguous response. Never blindly retried. |
| `SUBMITTING` | `FAILED` | `SubmissionService.execute_submission` | Submission error or missing submission control. |

---

## 5. Security & Isolation

- **Tenant Isolation**: All operations (`approve`, `revoke`, `submit`, `audit`) mandate candidate ownership (`user_id == application.user_id`). Cross-tenant access is rejected with `ApprovalRequiredError` or HTTP 403/404.
- **Secret Redaction**: `AuditService` automatically redacts sensitive dictionary keys (`token`, `password`, `cookie`, `secret`, `authorization`) to guarantee security logs contain zero candidate credentials.
- **Idempotency Guarantee**: Submitting an application that is already in `SUBMITTED` state immediately raises `AlreadySubmittedError` without executing any browser clicks or mutating existing submission timestamps.
