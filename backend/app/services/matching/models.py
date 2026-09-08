from dataclasses import dataclass, field
from typing import Dict, List, Optional
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile


def candidate_to_embedding_text(candidate: CandidateProfile) -> str:
    """
    Creates a clean, deterministic textual representation of the candidate profile
    for vector embedding generation.
    """
    profile = candidate.resume_profile
    prefs = candidate.preferences

    target_roles = ", ".join(prefs.get("target_roles", [])) or "Software Engineer"
    skills = ", ".join(profile.skills or prefs.get("required_skills", [])) or "Software Development"

    experience_bullets = []
    for exp in profile.experience:
        company = exp.company or "Company"
        role = exp.role or "Engineer"
        desc = exp.description or ""
        experience_bullets.append(f"{role} at {company}: {desc}")
    experience_text = "\n".join(experience_bullets) if experience_bullets else "Candidate professional experience."

    project_bullets = []
    for proj in profile.projects:
        name = proj.name or "Project"
        desc = proj.description or ""
        stack = ", ".join(proj.tech_stack)
        project_bullets.append(f"{name} ({stack}): {desc}")
    projects_text = "\n".join(project_bullets) if project_bullets else "Technical projects."

    sections = [
        f"Target Roles: {target_roles}",
        f"Key Skills: {skills}",
        f"Experience Summary: {profile.summary or ''}",
        f"Work Experience:\n{experience_text}",
        f"Projects:\n{projects_text}",
        f"Education: {', '.join(e.degree or '' for e in profile.education if e.degree)}",
    ]
    return "\n\n".join(s.strip() for s in sections if s.strip())


def job_to_embedding_text(job: JobPosting) -> str:
    """
    Creates a clean, deterministic textual representation of a job posting
    for vector embedding generation.
    """
    skills_text = ", ".join(job.skills) if job.skills else ""
    sections = [
        f"Job Title: {job.title}",
        f"Company: {job.company}",
        f"Location: {job.location or 'Remote'}",
        f"Remote Policy: {job.remote_type}",
        f"Experience Level: {job.experience_level or 'Not Specified'}",
        f"Required Skills: {skills_text}",
        f"Job Description:\n{job.description[:1500]}",
    ]
    return "\n\n".join(s.strip() for s in sections if s.strip())


@dataclass
class HardFilterEvaluation:
    passed: bool
    failed_constraints: List[str] = field(default_factory=list)
    unknown_constraints: List[str] = field(default_factory=list)
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class SkillMatchEvaluation:
    score: float
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    total_job_skills: int = 0


@dataclass
class RoleMatchEvaluation:
    score: float
    matched_role: Optional[str] = None
    similarity_reason: str = ""


@dataclass
class ExperienceMatchEvaluation:
    score: float
    candidate_level: str = ""
    job_level: str = ""
    reason: str = ""


@dataclass
class SemanticMatchEvaluation:
    score: Optional[float]
    is_fallback: bool
    warning: Optional[str] = None
