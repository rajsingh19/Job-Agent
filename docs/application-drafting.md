# Phase 6 — Application Drafting & Review Package

## 1. Overview & Architecture

Phase 6 implements the **application preparation and drafting layer**. The system consumes:
- `CandidateProfile`
- Selected `Resume`
- Discovered `JobPosting`
- Resolved `ApplicationRoute` (Phase 5)

and synthesizes an inspectable, validated `ApplicationDraft` and `ReviewPackage`.

```text
CandidateProfile + Available Resumes + JobPosting + ApplicationRoute
                              |
                              v
                 [1. ResumeSelector]
           (Selects best matching resume)
                              |
                              v
             [2. CandidateApplicationContext]
   (Derived truthful view: contact, education, skills,
        experience, projects, links, preferences)
                              |
                              v
            [3. ApplicationFieldMapper]
(Maps standard form fields: name, email, phone, links, etc.)
                              |
                              v
           [4. QuestionClassifier & Answerer]
 (Classifies custom questions; answers factual & subjective;
   flags sensitive/unsupported questions as requires_user_input)
                              |
                              v
            [5. CoverLetterGenerator]
 (Tailored, truthful letter grounded in candidate skills/projects)
                              |
                              v
          [6. ApplicationDraftValidator]
 (Format checking, required fields, truthfulness verification)
                              |
                              v
          [7. ReviewPackageGenerator]
(Consolidated package: fields, Q&A, letter, warnings, status)
                              |
                              v
           [8. Application Persistence]
 (Persists Application with status PENDING_REVIEW or REQUIRES_USER_ACTION)
```

> [!IMPORTANT]
> **Core Principle: Human-In-The-Loop**
> - **NO APPLICATION SUBMISSION**: Phase 6 prepares and validates drafts. It never automatically clicks submit or interacts with live ATS sites.
> - **NO BROWSER AUTOMATION**: Browser automation belongs strictly to Phase 7.
> - **ZERO FABRICATION**: The system never invents employers, dates, degrees, certifications, or skills.
> - **SENSITIVE SAFEGUARDS**: Legal, demographic, visa sponsorship, and unconfigured compensation questions strictly flag `requires_user_input = True`.

---

## 2. Core Modules

### 1. Resume Selection (`ResumeSelector`)
- Evaluates available candidate resumes against the job posting title and required skills.
- Automatically selects single resumes or best matching resumes.
- If multiple resumes have similar match scores (score delta < 0.15), it selects the top resume and flags `requires_user_input = True`.
- Enforces user ownership; attempting to select another user's resume raises an authorization error.

### 2. Candidate Application Context (`CandidateApplicationContext`)
A derived, non-hallucinated view compiling:
- Candidate contact info (name, email, phone, location)
- Online links (LinkedIn, GitHub, Portfolio)
- Real education history, skills, experience, and projects
- Explicit user preferences (work authorization, sponsorship required, availability, expected salary)

### 3. Field Mapping (`ApplicationFieldMapper`)
Normalizes form field labels and maps them to canonical context fields:
- Supported field types: `TEXT`, `EMAIL`, `PHONE`, `URL`, `DATE`, `NUMBER`, `TEXTAREA`, `SELECT`, `MULTI_SELECT`, `BOOLEAN`, `FILE`, `UNKNOWN`.
- Data lineage priority: `USER_INPUT` > `USER_PREFERENCE` > `CANDIDATE_PROFILE` > `RESUME` > `DERIVED` > `UNKNOWN`.
- Ambiguous/unmappable fields are tagged with `FieldSource.UNKNOWN` and require explicit user input.

### 4. Custom Question Classification & Grounded Answering (`QuestionClassifier` & `QuestionAnswerer`)
- Categorizes questions into `WORK_AUTHORIZATION`, `SALARY`, `AVAILABILITY`, `PERSONAL_FACT`, `EDUCATION`, `EXPERIENCE`, `SKILL`, `MOTIVATION`, `ROLE_FIT`, `PROJECT`, `BEHAVIORAL`, `OTHER`.
- **Factual questions** (e.g. graduation year, GPA, skills present) are answered with `confidence = 1.0` and `requires_review = False`.
- **Sensitive questions** (sponsorship, legal authorization, disability, expected salary) strictly set `answer = None` and `requires_user_input = True` unless explicitly supplied by the candidate in profile preferences.
- **Subjective questions** (motivation, why join) are grounded in the candidate's actual skills and projects, setting `requires_review = True`.
- Resilient fallback: if the AI provider is unavailable, answers use grounded deterministic templates rather than failing.

### 5. Tailored Cover Letter (`CoverLetterGenerator`)
- Generates professional, tailored cover letters grounded strictly in real candidate skills and projects.
- Never invents technologies or companies.
- Offline resiliency: if AI is unavailable, gracefully sets `cover_letter = None` with a warning without blocking draft creation.

### 6. Draft Validation (`ApplicationDraftValidator`)
- Enforces format correctness (email syntax, phone minimum 7 digits, URL schemes).
- Verifies all required fields are filled or marked `requires_user_input`.
- Verifies anti-fabrication truthfulness: answers claiming unverified employers or certifications are flagged with warnings.

### 7. Review Package (`ReviewPackageGenerator`)
Assembles the complete package for user inspection:
- Target job information (title, company, apply URL)
- Selected resume metadata
- Populated form fields and custom Q&A
- Cover letter
- Missing fields and warnings
- `screenshots = []` (extensible for Phase 7 Playwright capture)

---

## 3. REST API Endpoints

### 1. Create Application Draft
`POST /api/v1/jobs/{job_id}/application-draft`
- **Headers**: `X-User-Id: <user_id>`
- **Body** (optional):
```json
{
  "resume_id": "optional_resume_id",
  "custom_questions": [
    {"question_id": "q1", "question": "Why do you want to join our company?"}
  ],
  "include_cover_letter": true
}
```
- **Response**: `ApplicationDraft`

### 2. Get Application Draft
`GET /api/v1/applications/{application_id}/draft`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `ApplicationDraft`

### 3. Validate Application Draft
`POST /api/v1/applications/{application_id}/validate`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `ApplicationDraftValidationResponse`

### 4. Get Review Package
`GET /api/v1/applications/{application_id}/review`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `ApplicationReviewPackageResponse`

---

## 4. Multi-Tenant Security & Isolation

- All drafting and review endpoints require authenticated `X-User-Id`.
- User A cannot access, view, or validate User B's application drafts or review packages.
- No passwords, session secrets, or internal filesystem paths are exposed in API responses or database records.
