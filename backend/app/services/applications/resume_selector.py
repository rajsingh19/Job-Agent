import logging
from typing import List, Optional
from app.models.job import JobPosting
from app.models.resume import Resume
from app.schemas.resume import CandidateProfile
from app.services.applications.models import SelectedResumeResult

logger = logging.getLogger(__name__)


class ResumeSelector:
    """
    Evaluates available candidate resumes against a job posting and selects
    the most relevant resume. Enforces user authorization boundaries.
    """

    @staticmethod
    def select_resume(
        user_id: str,
        candidate_profile: CandidateProfile,
        job: JobPosting,
        available_resumes: List[Resume],
        requested_resume_id: Optional[str] = None,
    ) -> SelectedResumeResult:
        if not available_resumes:
            raise ValueError(f"No resumes available for user '{user_id}'.")

        # 1. If explicit resume requested, verify ownership and return
        if requested_resume_id:
            matching = [r for r in available_resumes if str(r.id) == requested_resume_id and str(r.user_id) == user_id]
            if not matching:
                raise ValueError(
                    f"Requested resume '{requested_resume_id}' not found or unauthorized for user '{user_id}'."
                )
            selected = matching[0]
            return SelectedResumeResult(
                resume_id=str(selected.id),
                resume_name=selected.name,
                match_score=1.0,
                confidence=1.0,
                requires_user_input=False,
                selection_reason="Explicitly selected by user.",
            )

        # 2. Single resume available
        if len(available_resumes) == 1:
            r = available_resumes[0]
            return SelectedResumeResult(
                resume_id=str(r.id),
                resume_name=r.name,
                match_score=1.0,
                confidence=1.0,
                requires_user_input=False,
                selection_reason="Only available resume in candidate profile.",
            )

        # 3. Multiple resumes: calculate relevance score based on skills and role
        job_skills = {s.lower() for s in (job.skills or [])}
        job_title_tokens = set((job.title or "").lower().split())

        scored_resumes = []
        for resume in available_resumes:
            parsed = resume.parsed_profile or {}
            resume_skills = {s.lower() for s in parsed.get("skills", [])}

            # Skill overlap
            overlap = len(job_skills.intersection(resume_skills))
            skill_score = (overlap / len(job_skills)) if job_skills else 0.5

            # Title / experience keyword overlap
            exp_text = " ".join(
                [f"{e.get('role', '')} {e.get('description', '')}" for e in parsed.get("experience", [])]
            ).lower()
            title_matches = sum(1 for token in job_title_tokens if token in exp_text)
            title_score = (title_matches / len(job_title_tokens)) if job_title_tokens else 0.5

            # Preference to default resume if tied
            default_bonus = 0.05 if resume.is_default else 0.0

            total_score = (skill_score * 0.6) + (title_score * 0.4) + default_bonus
            scored_resumes.append((total_score, resume))

        # Sort descending by score
        scored_resumes.sort(key=lambda x: x[0], reverse=True)
        top_score, top_resume = scored_resumes[0]
        runner_up_score, _ = scored_resumes[1]

        delta = top_score - runner_up_score
        if delta < 0.15:
            # Ambiguous selection: scores are very close
            return SelectedResumeResult(
                resume_id=str(top_resume.id),
                resume_name=top_resume.name,
                match_score=round(top_score, 2),
                confidence=0.60,
                requires_user_input=True,
                selection_reason=f"Ambiguous match between '{top_resume.name}' and runner-up (delta={delta:.2f}); user review recommended.",
            )

        return SelectedResumeResult(
            resume_id=str(top_resume.id),
            resume_name=top_resume.name,
            match_score=round(top_score, 2),
            confidence=0.90,
            requires_user_input=False,
            selection_reason=f"Selected based on highest skill & experience relevance to '{job.title}'.",
        )
