# Phase 4 — Job Matching & Semantic Ranking Engine

## 1. Overview & Architecture

The Job Matching and Semantic Ranking Engine evaluates active job postings against a candidate's structured profile (`CandidateProfile = ResumeProfile + UserPreference`). It produces a normalized `0–100` match score, evaluates hard candidate constraints, provides explainable insights (matched skills, missing skills, match reasons), and computes a data confidence quality indicator.

```text
                     +----------------------------------------+
                     |    CandidateProfile + JobPosting       |
                     +----------------------------------------+
                                         |
         +-------------------------------+-------------------------------+
         |                               |                               |
         v                               v                               v
+------------------+           +-------------------+           +-------------------+
| HardFilterEngine |           |  KeywordMatcher   |           |  SemanticMatcher  |
| (Pass / Fail /   |           | (Synonyms, Word   |           | (Cosine Similarity|
|  Unknown)        |           |  Boundaries)      |           |  + Fallback)      |
+------------------+           +-------------------+           +-------------------+
         |                               |                               |
         |             +-----------------+----------------+              |
         |             |                                  |              |
         |             v                                  v              v
         |     +----------------+                 +----------------+     |
         |     |  RoleMatcher   |                 |ExperienceMatc. |     |
         |     | (Title Cluster)|                 | (Level Ladder) |     |
         |     +----------------+                 +----------------+     |
         |             |                                  |              |
         +-------------+-----------------+----------------+--------------+
                                         |
                                         v
                     +----------------------------------------+
                     |              JobScorer                 |
                     |  • Weighted Score (0–100)              |
                     |  • Dynamic Fallback Weight Scaling     |
                     |  • Explainability Engine               |
                     |  • Confidence Calculation              |
                     +----------------------------------------+
                                         |
                                         v
                     +----------------------------------------+
                     |            JobMatchResult              |
                     +----------------------------------------+
```

---

## 2. Hard Constraint Filtering (`HardFilterEngine`)

Hard constraint filtering evaluates explicit user boundaries against job properties. Hard constraint results are kept strictly separate from the relevance score (`match_score`), ensuring that non-passing jobs can still reflect their semantic relevance without polluting user constraints.

### Evaluated Constraints:
1. **Excluded Companies**: Rejects companies listed in candidate's `excluded_companies` (case-insensitive substring match).
2. **Work Mode / Remote Preference**:
   - `REMOTE` candidate requires `REMOTE` or `HYBRID` job.
   - `ON_SITE` candidate requires `ON_SITE` or `HYBRID` job.
   - `HYBRID` or `ANY` accepts any work mode.
3. **Preferred Locations**: Matches city / state / country tokens in location strings. If location is unlisted on the job, it yields `UNKNOWN` rather than a hard failure.
4. **Compensation / Stipend**: Evaluates candidate `minimum_stipend` against job's `stipend_max` / `stipend_min`. If job compensation is omitted, it yields `UNKNOWN` unless compensation is explicitly configured as mandatory.

### Constraint Evaluation Result:
```json
{
  "passed": true,
  "failed_constraints": [],
  "unknown_constraints": ["compensation"]
}
```

---

## 3. Scoring Formula & Dynamic Fallback

### Standard Weighted Composite Score
```text
match_score = (keyword_score * 0.30)
            + (semantic_score * 0.35)
            + (role_score * 0.20)
            + (experience_score * 0.15)
```

| Component | Default Weight | Description |
|---|---|---|
| `KeywordMatcher` | `0.30` | Skill overlap with synonym expansion (`JS` -> `JavaScript`, `Postgres` -> `PostgreSQL`) and false-positive word boundary protection. |
| `SemanticMatcher` | `0.35` | Vector cosine similarity between deterministic candidate representation and job posting description. |
| `RoleMatcher` | `0.20` | Semantic role cluster and title similarity (`SWE` <-> `Software Engineer`, `Backend Lead` <-> `Senior Backend Developer`). |
| `ExperienceMatcher` | `0.15` | Experience ladder delta comparison (Intern -> Junior -> Mid-Level -> Senior -> Lead/Principal). |

### Dynamic Weight Redistribution on Provider Outage
If the external embedding provider times out, fails, or has invalid credentials:
1. `semantic_score` is set to `None`.
2. `is_fallback = True` and a descriptive warning is added.
3. The remaining component weights (0.30 + 0.20 + 0.15 = 0.65) are dynamically normalized to sum to `1.0`:
   - `keyword_weight`: $0.30 / 0.65 \approx 0.4615$
   - `role_weight`: $0.20 / 0.65 \approx 0.3077$
   - `experience_weight`: $0.15 / 0.65 \approx 0.2308$

---

## 4. Confidence Metric

Confidence is computed as a bounded float `[0.0, 1.0]` representing the completeness and reliability of input data:
- **Baseline**: `1.0`
- **Missing / Sparse Candidate Skills**: `-0.15`
- **Fallback Parser Used**: `-0.10`
- **Embedding Provider Outage (Fallback Active)**: `-0.20`
- **Job Skills Missing**: `-0.10`
- **Job Experience Level Missing**: `-0.05`
- **Hard Filter Unknowns**: `-0.05` per unknown constraint

---

## 5. API Endpoints

### 1. Match Single Job
`POST /api/v1/jobs/{job_id}/match?resume_id={optional_resume_id}`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `JobMatchResult`

### 2. Match Multiple Jobs
`POST /api/v1/jobs/match`
- **Headers**: `X-User-Id: <user_id>`
- **Body**:
```json
{
  "resume_id": "optional_resume_id",
  "min_score": 50.0,
  "hard_match_only": false
}
```
- **Response**: `List[JobMatchResult]`

### 3. Get Ranked Job Feed
`GET /api/v1/jobs/ranked?min_score=60.0&hard_match_only=true&limit=20&offset=0`
- **Headers**: `X-User-Id: <user_id>`
- **Response**: `RankedJobsResponse`
```json
{
  "results": [ ... ],
  "total_matched": 18,
  "total_hard_matched": 12,
  "average_score": 78.4,
  "candidate_id": "user_123"
}
```

---

## 6. Security & Multi-Tenancy

- Matches are calculated dynamically per authenticated `X-User-Id` request context.
- User A's candidate preferences and uploaded resume profiles are strictly isolated and cannot be accessed or matched against by User B.
- No database mutations occur during matching calculations.
