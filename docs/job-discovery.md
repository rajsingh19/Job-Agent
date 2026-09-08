# Job Discovery & Normalization Architecture

## Overview
Phase 3 establishes an extensible, multi-source job discovery engine capable of ingesting raw postings from official candidate job board APIs, ATS endpoints, and generic browser sources. Postings are normalized, deduplicated using deterministic source hashing and fuzzy matching, and persisted idempotently in the database.

---

## Multi-Source Discovery Pipeline

```text
JobSearchQuery (keywords, locations, remote_type, limit, sources)
      ↓
JobDiscoveryService (orchestrator with bounded concurrency & retries)
      ↓
JobSourceRegistry
   ├── APISource (GreenhouseSource, LeverSource)
   ├── ATSSource (AshbySource)
   └── BrowserSource (GenericBrowserDiscovery)
      ↓
Raw Postings Extraction (Isolated per source — failures never crash the run)
      ↓
JobNormalizer (Standardize titles, company names, locations, remote types, skills)
      ↓
JobDeduplicator (Deterministic SHA-256 source hash + Cross-source fuzzy deduplication)
      ↓
JobRepository (Idempotent database upsert)
      ↓
Unified DiscoveryResult (`jobs`, `total_found`, `total_unique`, `source_errors`)
```

---

## Source Categories & Supported Providers

### 1. Official API Sources (`APISource`)
- **Greenhouse (`GreenhouseSource`)**:
  - Uses public API: `https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`.
  - Supports configurable company slugs (e.g. `gitlab`, `canonical`, `cloudflare`, `stripe`).
  - Extracts title, location, departments, clean description, and direct application URL.
- **Lever (`LeverSource`)**:
  - Uses public API: `https://api.lever.co/v0/postings/{company}?mode=json`.
  - Supports configurable company slugs (e.g. `palantir`, `netflix`, `affirm`).
  - Extracts categories (location, team), clean plain text description, and direct apply URL.

### 2. Public ATS Sources (`ATSSource`)
- **Ashby (`AshbySource`)**:
  - Uses public posting API: `https://api.ashbyhq.com/posting-api/job-board/{company}`.
  - Ingests structured roles with remote indicators and application links.

### 3. Browser-Based Discovery (`BrowserSource`)
- **`GenericBrowserDiscovery`**:
  - Framework for scraping job portals and custom company career pages using DOM selector rules (`BrowserDiscoveryConfig`).
  - **Bot Protection & Login Walls**: Automatically detects CAPTCHA (`recaptcha`, `cf-turnstile`) or mandatory login screens and reports a structured error without attempting unauthorized bypasses.
  - Prepares the foundation for future portal connectors (LinkedIn, Internshala, Wellfound, Naukri, Indeed, Glassdoor, Shine).

---

## Normalization & Deduplication

### Normalization Rules
1. **Company Names**: Strips trailing corporate legal suffixes (`Inc.`, `LLC`, `Corp.`, `Pvt Ltd`) for matching.
2. **Job Titles**: Standardizes abbreviations (e.g., `Sr.` -> `Senior`, `SWE` -> `Software Engineer`, `Dev` -> `Developer`) and removes bracketed location tags (`[Remote]`, `(US Only)`).
3. **Remote Types**: Detects keywords in title and description to map into `REMOTE`, `HYBRID`, `ON_SITE`, or `ANY`.
4. **Skills Extraction**: Automatically maps technical keywords to canonical casing (`FastAPI`, `PostgreSQL`, `TypeScript`, `Docker`, `PyTorch`).

### Deduplication Rules
1. **Deterministic Hashing**:
   - Computes `sha256(f"{source}:{external_id}")` when official ID exists.
   - Computes `sha256(f"{company}:{title}:{location}:{apply_url}")` as fallback.
2. **Cross-Source Fuzzy Deduplication**:
   - Detects when the same role appears across both direct ATS and aggregators.
   - Calculates title token similarity (> 0.75) and verifies company and location compatibility before merging.

---

## REST API Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/v1/jobs/discover` | Explicitly triggers job discovery with `JobSearchQuery` |
| `GET` | `/api/v1/jobs` | Queries and filters saved jobs with pagination (`JobFilter`) |
| `GET` | `/api/v1/jobs/{job_id}` | Retrieves details for an individual job posting |

---

## Configuration Variables

```env
JOB_DISCOVERY_TIMEOUT_SECONDS=30.0
JOB_DISCOVERY_MAX_RETRIES=3
JOB_DISCOVERY_MAX_CONCURRENCY=5
JOB_DISCOVERY_DEFAULT_LIMIT=50
```
