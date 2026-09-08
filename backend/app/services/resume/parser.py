from abc import ABC, abstractmethod
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import ValidationError
from app.schemas.resume import (
    ResumeProfile,
    EducationItem,
    ExperienceItem,
    ProjectItem,
    CertificationItem,
)
from app.services.ai.provider import LLMProvider
from app.services.exceptions import LLMParseFailedError, ProfileValidationError

logger = logging.getLogger(__name__)

SYSTEM_RESUME_PARSER_PROMPT = """
You are an expert, truthful resume parsing assistant.
Your task is to parse unstructured resume text into a strict structured JSON profile matching the schema.

MANDATORY RULES:
1. Extract ONLY information explicitly present in the resume text.
2. NEVER invent qualifications, experience, skills, certifications, or contact details.
3. NEVER infer or extrapolate unstated years of experience.
4. Leave any missing or uncertain fields as empty lists or null.
5. Preserve accurate URLs (GitHub, LinkedIn, personal portfolios) if mentioned.
6. Extract clean skills as individual items in the skills array.
7. Return valid JSON only, without commentary.

JSON Output Schema:
{
  "name": string or null,
  "email": string or null,
  "phone": string or null,
  "location": string or null,
  "summary": string or null,
  "education": [
    {
      "institution": string,
      "degree": string or null,
      "field_of_study": string or null,
      "start_date": string or null,
      "end_date": string or null,
      "gpa": string or null,
      "highlights": [string]
    }
  ],
  "experience": [
    {
      "company": string,
      "role": string,
      "location": string or null,
      "start_date": string or null,
      "end_date": string or null,
      "is_current": boolean,
      "description": string or null,
      "highlights": [string],
      "skills_used": [string]
    }
  ],
  "projects": [
    {
      "name": string,
      "role": string or null,
      "description": string or null,
      "url": string or null,
      "tech_stack": [string],
      "highlights": [string]
    }
  ],
  "skills": [string],
  "links": { "github": string, "linkedin": string, ... },
  "certifications": [
    {
      "name": string,
      "issuer": string,
      "issue_date": string or null,
      "expiry_date": string or null,
      "credential_id": string or null,
      "url": string or null
    }
  ],
  "achievements": [string],
  "languages": [string]
}
"""


class ResumeParser(ABC):
    """Abstract interface for resume parsing."""

    @abstractmethod
    async def parse(self, resume_text: str) -> ResumeProfile:
        pass


class LLMResumeParser(ResumeParser):
    """LLM-backed resume parser with strict validation and ground-truth enforcement."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def parse(self, resume_text: str) -> ResumeProfile:
        prompt = f"Resume text to parse:\n\n---\n{resume_text}\n---"
        raw_json = await self.llm.generate_json(prompt=prompt, system_prompt=SYSTEM_RESUME_PARSER_PROMPT)

        # Validate with Pydantic
        warnings: List[str] = []
        try:
            # Clean and validate basic fields
            email = raw_json.get("email")
            if email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email.strip()):
                warnings.append(f"Ignored invalid email format: '{email}'")
                raw_json["email"] = None

            profile = ResumeProfile(
                name=raw_json.get("name"),
                email=raw_json.get("email"),
                phone=raw_json.get("phone"),
                location=raw_json.get("location"),
                summary=raw_json.get("summary"),
                education=[EducationItem(**item) for item in raw_json.get("education", []) if isinstance(item, dict) and item.get("institution")],
                experience=[ExperienceItem(**item) for item in raw_json.get("experience", []) if isinstance(item, dict) and item.get("company") and item.get("role")],
                projects=[ProjectItem(**item) for item in raw_json.get("projects", []) if isinstance(item, dict) and item.get("name")],
                skills=[s.strip() for s in raw_json.get("skills", []) if isinstance(s, str) and s.strip()],
                links={k: v for k, v in raw_json.get("links", {}).items() if isinstance(v, str) and v.startswith("http")},
                certifications=[CertificationItem(**item) for item in raw_json.get("certifications", []) if isinstance(item, dict) and item.get("name") and item.get("issuer")],
                achievements=[a for a in raw_json.get("achievements", []) if isinstance(a, str)],
                languages=[l for l in raw_json.get("languages", []) if isinstance(l, str)],
                warnings=warnings,
                low_confidence=False,
                raw_text=resume_text,
            )
            return profile

        except (ValidationError, TypeError) as e:
            logger.error(f"Profile schema validation failed on LLM output: {e}")
            raise ProfileValidationError(f"Invalid structured output from LLM: {str(e)}")


class FallbackResumeParser(ResumeParser):
    """
    Deterministic rule-based & regex parser used when LLM is unavailable or fails.
    Marks output with low_confidence = True and adds explicit warnings.
    """

    # Common technical skill keywords for deterministic identification
    KNOWN_SKILLS = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "sql", "html",
        "css", "react", "next.js", "node.js", "fastapi", "django", "flask", "express", "postgresql",
        "mysql", "sqlite", "mongodb", "redis", "docker", "kubernetes", "aws", "gcp", "azure",
        "git", "linux", "rest api", "graphql", "playwright", "selenium", "machine learning", "pandas",
    ]

    async def parse(self, resume_text: str) -> ResumeProfile:
        warnings = ["Extracted using fallback deterministic parser due to LLM unavailability. Please review details."]

        # 1. Email extraction
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resume_text)
        email = email_match.group(0) if email_match else None

        # 2. Phone extraction
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", resume_text)
        phone = phone_match.group(0) if phone_match else None

        # 3. Links extraction
        links = {}
        github_match = re.search(r"https?://(?:www\.)?github\.com/[a-zA-Z0-9_-]+", resume_text, re.IGNORECASE)
        if github_match:
            links["github"] = github_match.group(0)

        linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+", resume_text, re.IGNORECASE)
        if linkedin_match:
            links["linkedin"] = linkedin_match.group(0)

        # 4. Name extraction heuristic (first non-empty line with letters)
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        name = None
        for line in lines[:5]:
            if len(line.split()) in [2, 3, 4] and not any(c in line for c in "@/:0123456789"):
                name = line
                break

        # 5. Skills extraction
        text_lower = resume_text.lower()
        skills = []
        for skill in self.KNOWN_SKILLS:
            # Word boundary search
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text_lower):
                # Format skill nicely
                skills.append(skill.title() if len(skill) > 3 else skill.upper())

        # 6. Education extraction heuristic
        education = []
        edu_match = re.search(r"(?:education|academic|university|college)([\s\S]{1,400}?)(?:experience|projects|skills|$)", text_lower)
        if edu_match:
            edu_snippet = edu_match.group(1).strip()
            # Look for degree terms
            degree_match = re.search(r"(bachelor|master|b\.s\.|m\.s\.|b\.tech|phd|diploma)[^\n]*", edu_snippet, re.IGNORECASE)
            degree_str = degree_match.group(0) if degree_match else "Degree"
            education.append(
                EducationItem(
                    institution="Educational Institution (Extracted from Resume)",
                    degree=degree_str,
                    highlights=[edu_snippet[:150]],
                )
            )

        # 7. Experience extraction heuristic
        experience = []
        exp_match = re.search(r"(?:experience|employment|work history)([\s\S]{1,600}?)(?:education|projects|skills|$)", text_lower)
        if exp_match:
            exp_snippet = exp_match.group(1).strip()
            experience.append(
                ExperienceItem(
                    company="Experience details in resume",
                    role="Candidate Role",
                    description=exp_snippet[:300],
                )
            )

        return ResumeProfile(
            name=name,
            email=email,
            phone=phone,
            location=None,
            summary=None,
            education=education,
            experience=experience,
            projects=[],
            skills=skills,
            links=links,
            certifications=[],
            achievements=[],
            languages=[],
            warnings=warnings,
            low_confidence=True,
            raw_text=resume_text,
        )
