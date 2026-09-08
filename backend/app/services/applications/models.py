from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.schemas.application_draft import CandidateApplicationContext
from app.schemas.resume import CandidateProfile


@dataclass
class SelectedResumeResult:
    """Result of resume selection for an application draft."""
    resume_id: str
    resume_name: str
    match_score: float
    confidence: float
    requires_user_input: bool
    selection_reason: str


def build_candidate_application_context(
    candidate_profile: CandidateProfile,
    resume: Optional[Resume] = None,
    preferences: Optional[UserPreference] = None,
) -> CandidateApplicationContext:
    """
    Builds a deterministic, non-hallucinated application context combining candidate
    profile, parsed resume data, and user preferences.
    Priority: Explicit preferences/profile > parsed resume.
    """
    resume_data: Dict[str, Any] = {}
    if resume and resume.parsed_profile:
        resume_data = resume.parsed_profile

    # Extract name, email, phone with precedence
    name = (
        candidate_profile.resume_profile.name
        or resume_data.get("name")
        or "Applicant"
    )
    email = (
        candidate_profile.resume_profile.email
        or resume_data.get("email")
        or "applicant@example.com"
    )
    phone = (
        candidate_profile.resume_profile.phone
        or resume_data.get("phone")
    )
    location = (
        candidate_profile.resume_profile.location
        or resume_data.get("location")
    )

    # Links
    links = candidate_profile.resume_profile.links or resume_data.get("links", {})
    linkedin_url = links.get("linkedin")
    github_url = links.get("github")
    portfolio_url = links.get("portfolio") or links.get("website")

    # Skills - unique union of profile and resume skills
    profile_skills = list(candidate_profile.resume_profile.skills or [])
    resume_skills = list(resume_data.get("skills", []))
    all_skills = list(dict.fromkeys(profile_skills + resume_skills))

    # Experience list of dicts
    experience: List[Dict[str, Any]] = []
    if candidate_profile.resume_profile.experience:
        for exp in candidate_profile.resume_profile.experience:
            experience.append(exp.model_dump())
    elif "experience" in resume_data:
        experience = list(resume_data["experience"])

    # Education list of dicts
    education: List[Dict[str, Any]] = []
    if candidate_profile.resume_profile.education:
        for edu in candidate_profile.resume_profile.education:
            education.append(edu.model_dump())
    elif "education" in resume_data:
        education = list(resume_data["education"])

    # Projects list of dicts
    projects: List[Dict[str, Any]] = []
    if candidate_profile.resume_profile.projects:
        for proj in candidate_profile.resume_profile.projects:
            projects.append(proj.model_dump())
    elif "projects" in resume_data:
        projects = list(resume_data["projects"])

    # Achievements & Languages
    achievements = list(candidate_profile.resume_profile.achievements or resume_data.get("achievements", []))
    languages = list(candidate_profile.resume_profile.languages or resume_data.get("languages", []))

    # Explicit preferences
    preferred_roles = []
    work_auth = None
    sponsorship = None
    avail_from = None
    expected_salary = None

    if preferences:
        preferred_roles = list(preferences.target_roles or [])
        extra = preferences.additional_preferences or {}
        work_auth = extra.get("work_authorization")
        sponsorship = extra.get("sponsorship_required")
        avail_from = extra.get("available_from")
        expected_salary = extra.get("expected_salary")

    return CandidateApplicationContext(
        name=name,
        email=email,
        phone=phone,
        location=location,
        linkedin_url=linkedin_url,
        github_url=github_url,
        portfolio_url=portfolio_url,
        education=education,
        skills=all_skills,
        experience=experience,
        projects=projects,
        achievements=achievements,
        languages=languages,
        preferred_roles=preferred_roles,
        work_authorization=work_auth,
        sponsorship_required=sponsorship,
        available_from=avail_from,
        expected_salary=expected_salary,
    )
