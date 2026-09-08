# Resume Processing & Candidate Profile Architecture

## Overview
Phase 2 implements an end-to-end ingestion and structured extraction pipeline for candidate resumes (PDF & DOCX), paired with authoritative user preferences to construct unified candidate profiles for subsequent job matching and application drafting.

---

## Processing Pipeline

```text
Resume File (PDF / DOCX)
    ↓
Upload Endpoint (`POST /api/v1/resumes`)
    ↓
Validation (MIME type, extension, size limit, path sanitization, SHA-256 hash)
    ↓
Isolated Storage (`storage/resumes/<uuid>.<ext>`)
    ↓
Text Extraction (`PDFResumeExtractor` / `DOCXResumeExtractor`)
    ↓
LLM Structured Extraction (`LLMResumeParser`)
    ↓
[LLM Failure / Timeout / Unavailable] ──► Fallback Parser (`FallbackResumeParser`, low_confidence=True)
    ↓
Pydantic Schema Validation & Sanitization (`ResumeProfile`)
    ↓
Database Persistence (`resumes.parsed_profile`)
    ↓
Candidate Profile Join (`CandidateProfileService`)
    ↓
CandidateProfile = ResumeProfile + Authoritative UserPreferences
```

---

## Key Components

### 1. File Upload & Storage Security
- **Supported Formats**: PDF (`.pdf`), DOCX (`.docx`).
- **File Validation**: MIME verification (`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`), size limit (`max_resume_file_size_bytes`, default 10MB).
- **Sanitization & Traversal Protection**: User filenames are never used for disk storage paths. Files are assigned randomized UUID names (e.g. `d3b07384-d113-48b9-8e4a-5f09623e1b71.pdf`).
- **Path Leak Prevention**: API responses return sanitized relative references (`storage/resumes/...`), never exposing absolute internal filesystem paths.

### 2. Text Extraction Layer
- **`PDFResumeExtractor`**: Uses `pypdf` to extract text page-by-page. Detects encrypted/password-protected PDFs and scanned/image-only PDFs, returning `TEXT_EXTRACTION_REQUIRED`.
- **`DOCXResumeExtractor`**: Uses `python-docx` to extract text from paragraphs and embedded tables.
- **Corrupted File Detection**: Catches unreadable or corrupted files and returns `FILE_CORRUPTED`.

### 3. AI / LLM Provider Abstraction
- Provider abstraction (`LLMProvider`) supporting:
  - `OpenAILLMProvider` (OpenAI GPT-4o-mini / GPT-4o)
  - `GroqLLMProvider` (Llama-3.3-70b)
  - `OllamaLLMProvider` (Local Llama3)
  - `MockLLMProvider` (Deterministic local mock for tests)
- **Extraction Rules**:
  - Extract only information present in the resume.
  - Never invent qualifications, experience, skills, or dates.
  - Leave unknown/uncertain fields empty.
  - Preserve URLs (GitHub, LinkedIn).

### 4. Deterministic Fallback Parser
- If LLM provider is unavailable, times out, or returns malformed data:
  - Activates `FallbackResumeParser` using regex and heuristic extraction for email, phone, links, skills, and section blocks.
  - Sets `low_confidence = True`.
  - Appends warnings alerting the user to review the extracted fields.

### 5. Preference Authority & Non-Overwriting Guarantee
- **Rule**: Resume parsing **NEVER** overwrites explicit user preferences.
- Example: If a resume lists location as *"Delhi"* but user preferences specify *"Bangalore"*, the combined `CandidateProfile` preserves both independently.

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/resumes` | Upload a new PDF/DOCX resume |
| `GET` | `/api/v1/resumes` | List all uploaded resumes for user |
| `GET` | `/api/v1/resumes/{id}` | Get metadata for specific resume |
| `POST` | `/api/v1/resumes/{id}/parse` | Trigger extraction and parsing |
| `GET` | `/api/v1/resumes/{id}/profile` | Get structured resume profile |
| `GET` | `/api/v1/preferences` | Get authoritative user preferences |
| `PUT` | `/api/v1/preferences` | Update authoritative user preferences |
| `GET` | `/api/v1/profile` | Get combined `CandidateProfile` |

---

## Environment Variables

```env
# AI / LLM Provider
LLM_PROVIDER=openai # openai, groq, ollama, mock
LLM_API_KEY=your_key_here
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.2

# Storage & Upload Limits
MAX_RESUME_FILE_SIZE_BYTES=10485760 # 10 MB
```
