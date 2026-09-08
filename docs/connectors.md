# Phase 5 — ATS Detection & Connector Architecture

## 1. Overview & Goal

Phase 5 establishes a modular, extensible connector architecture that evaluates a discovered job posting (`JobPosting`) and determines the appropriate application routing mechanism (`ApplicationRoute`).

The connector layer operates strictly on detection, capability reporting, and routing. In accordance with safety principles, **no applications are submitted, no credentials/passwords are captured, and no anti-bot or authentication protections are bypassed.**

```text
                     +----------------------------------------+
                     |              JobPosting                |
                     +----------------------------------------+
                                         |
                                         v
                     +----------------------------------------+
                     |              ATSDetector               |
                     |  • Domain Pattern Matchers             |
                     |  • Source Metadata Analysis            |
                     |  • Signal Conflict Resolution          |
                     +----------------------------------------+
                                         |
                                         v (ATSDetectionResult)
                     +----------------------------------------+
                     |           ConnectorRegistry            |
                     |  • Platform -> PlatformConnector       |
                     |  • Generic Browser Fallback            |
                     +----------------------------------------+
                                         |
                                         v (PlatformConnector)
                     +----------------------------------------+
                     |            ConnectorRouter             |
                     |  • Route Decision & Requirements       |
                     |  • Honest Capability Reporting         |
                     +----------------------------------------+
                                         |
                                         v
                     +----------------------------------------+
                     |            ApplicationRoute            |
                     +----------------------------------------+
```

---

## 2. Supported Platforms & Detection Rules

The `PlatformType` enum defines canonical platforms:

| Platform | URL Pattern / Matcher | Application Method | Requires Browser |
|---|---|---|---|
| `GREENHOUSE` | `boards.greenhouse.io`, `job-boards.greenhouse.io`, `greenhouse.io` | `ATS` | False |
| `LEVER` | `jobs.lever.co`, `lever.co` | `ATS` | False |
| `ASHBY` | `jobs.ashbyhq.com`, `ashbyhq.com` | `ATS` | False |
| `LINKEDIN` | `linkedin.com` | `BROWSER` | True (Requires Login) |
| `INTERNSHALA` | `internshala.com` | `BROWSER` | True (Requires Login) |
| `NAUKRI` | `naukri.com` | `BROWSER` | True (Requires Login) |
| `SHINE` | `shine.com` | `BROWSER` | True (Requires Login) |
| `WELLFOUND` | `wellfound.com`, `angel.co` | `BROWSER` | True (Requires Login) |
| `GENERIC_ATS` | `myworkdayjobs.com`, `bamboohr.com`, `smartrecruiters.com`, `icims.com` | `BROWSER` | True |
| `BROWSER` | Generic career portal URLs | `BROWSER` | True |
| `UNKNOWN` | Missing, malformed, or unverified URL | `USER_ACTION` | True (Requires User Action) |

---

## 3. Detection Priority & Signal Conflicts

`ATSDetector` evaluates job metadata with the following deterministic priority:
1. **Apply URL Domain**: Primary signal (`boards.greenhouse.io` -> `GREENHOUSE`).
2. **Source URL Domain**: Secondary signal if apply URL domain is generic.
3. **Source / ATS Metadata**: Declared discovery source (`source="GREENHOUSE"` or `ats_provider="lever"`).
4. **Conflict Resolution**:
   - When apply URL domain and source metadata point to different specific platforms (e.g., `source="GREENHOUSE"` but `apply_url="jobs.lever.co/..."`), apply URL takes precedence.
   - The conflict is logged in `signals` and `warnings`, and confidence is reduced to account for ambiguity.

---

## 4. Connector Capabilities & Honest Reporting

`ConnectorCapabilities` defines the capability matrix. In Phase 5, all connectors report honest capabilities:

```python
class ConnectorCapabilities(BaseModel):
    can_discover_jobs: bool = True
    can_get_job_details: bool = True
    can_prepare_application: bool = False   # Phase 6
    can_fill_application: bool = False      # Phase 6/7
    can_upload_resume: bool = False         # Phase 7
    can_answer_questions: bool = False      # Phase 6
    can_submit_application: bool = False    # Phase 8 strictly
    requires_browser: bool
    requires_login: bool
    supports_persistent_session: bool
    requires_user_action: bool
```

`can_submit_application` is strictly `False` across all connectors in Phase 5.

---

## 5. REST API Endpoints

### 1. Detect Platform
`POST /api/v1/jobs/{job_id}/detect-platform`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `PlatformDetectResponse`
```json
{
  "job_id": "sec_job_gh_01",
  "platform": "greenhouse",
  "confidence": 0.98,
  "application_method": "ats",
  "requires_browser": false,
  "requires_user_action": false,
  "signals": [
    "apply_url_domain=boards.greenhouse.io -> greenhouse"
  ],
  "warnings": []
}
```

### 2. Get Application Route
`GET /api/v1/jobs/{job_id}/application-route`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `ApplicationRoute`
```json
{
  "job_id": "sec_job_gh_01",
  "platform": "greenhouse",
  "connector": "Greenhouse ATS Connector",
  "application_method": "ats",
  "capabilities": {
    "can_discover_jobs": true,
    "can_get_job_details": true,
    "can_prepare_application": false,
    "can_fill_application": false,
    "can_upload_resume": false,
    "can_answer_questions": false,
    "can_submit_application": false,
    "requires_browser": false,
    "requires_login": false,
    "supports_persistent_session": false,
    "requires_user_action": false
  },
  "confidence": 0.98,
  "requires_browser": false,
  "requires_login": false,
  "requires_user_action": false,
  "signals": ["apply_url_domain=boards.greenhouse.io -> greenhouse"],
  "warnings": []
}
```

### 3. List Registered Connectors
`GET /api/v1/connectors`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `List[ConnectorInfo]`

---

## 6. How Future Phases Extend Connectors

- **Phase 6 (Application Drafting)**: Introduces `prepare_application()` and `generate_answers()` methods.
- **Phase 7 (Browser Automation)**: Introduces Playwright-based form navigation, session authentication, and resume attachment.
- **Phase 8 (Approval & Submission)**: Enables `submit_application()` gated strictly behind explicit human review and state machine transitions.
