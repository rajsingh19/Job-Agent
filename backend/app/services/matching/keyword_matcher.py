import re
from typing import List, Set, Tuple
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile
from app.services.matching.models import SkillMatchEvaluation

# Canonical synonym mapping
SKILL_SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "react.js": "react",
    "reactjs": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "py": "python",
    "golang": "go",
    "k8s": "kubernetes",
    "tf": "terraform",
    "gcp": "google cloud",
    "aws": "amazon web services",
    "ml": "machine learning",
    "dl": "deep learning",
}


class KeywordMatcher:
    """
    Evaluates exact and normalized keyword/skill overlap between candidate and job.
    Avoids false positive substring matches.
    """

    @classmethod
    def _normalize_skill(cls, skill: str) -> str:
        s = skill.lower().strip()
        return SKILL_SYNONYMS.get(s, s)

    @classmethod
    def _extract_all_candidate_skills(cls, candidate: CandidateProfile) -> Set[str]:
        skills: Set[str] = set()

        # 1. ResumeProfile skills
        for s in candidate.resume_profile.skills:
            if s.strip():
                skills.add(cls._normalize_skill(s))

        # 2. Tech stack in projects
        for proj in candidate.resume_profile.projects:
            for s in proj.tech_stack:
                if s.strip():
                    skills.add(cls._normalize_skill(s))

        # 3. Skills used in experience
        for exp in candidate.resume_profile.experience:
            for s in exp.skills_used:
                if s.strip():
                    skills.add(cls._normalize_skill(s))

        # 4. User preferences required skills
        for s in candidate.preferences.get("required_skills", []):
            if s.strip():
                skills.add(cls._normalize_skill(s))

        return skills

    @classmethod
    def evaluate(cls, candidate: CandidateProfile, job: JobPosting) -> SkillMatchEvaluation:
        candidate_skills = cls._extract_all_candidate_skills(candidate)

        # 1. Job skills from normalized list
        job_skills = [s.strip() for s in job.skills if s.strip()]

        matched_skills: List[str] = []
        missing_skills: List[str] = []

        if job_skills:
            for skill in job_skills:
                norm_skill = cls._normalize_skill(skill)
                # Word-boundary check or exact normalized match
                is_matched = False
                if norm_skill in candidate_skills:
                    is_matched = True
                else:
                    # Check against candidate skill set elements with regex word boundary
                    pattern = r"\b" + re.escape(norm_skill) + r"\b"
                    for cs in candidate_skills:
                        if re.search(pattern, cs):
                            is_matched = True
                            break

                if is_matched:
                    matched_skills.append(skill)
                else:
                    missing_skills.append(skill)

            total_job_skills = len(job_skills)
            score = (len(matched_skills) / total_job_skills) * 100.0
        else:
            # If job has no extracted skills list, scan candidate skills against job description
            desc_lower = f"{job.title} {job.description}".lower()
            for cs in candidate_skills:
                # Word-boundary check to prevent "c" matching "c++"
                pattern = r"\b" + re.escape(cs) + r"\b"
                if re.search(pattern, desc_lower):
                    matched_skills.append(cs.title())

            total_job_skills = max(len(matched_skills), 1)
            score = min(100.0, len(matched_skills) * 20.0)

        # Clamp score to 0–100
        score = max(0.0, min(100.0, score))

        return SkillMatchEvaluation(
            score=round(score, 1),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            total_job_skills=total_job_skills,
        )
