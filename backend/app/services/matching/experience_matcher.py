from typing import Optional
from app.models.enums import ExperienceLevel
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile
from app.services.matching.models import ExperienceMatchEvaluation

LEVEL_HIERARCHY = {
    "INTERNSHIP": 1,
    "ENTRY_LEVEL": 2,
    "MID_LEVEL": 3,
    "SENIOR_LEVEL": 4,
    "LEAD": 5,
    "EXECUTIVE": 6,
}


class ExperienceMatcher:
    """
    Evaluates experience level compatibility between candidate and job posting.
    """

    @classmethod
    def _get_candidate_level(cls, candidate: CandidateProfile) -> str:
        # Preference level has priority
        pref_level = candidate.preferences.get("experience_level")
        if pref_level:
            val = pref_level.value if hasattr(pref_level, "value") else str(pref_level)
            return val.upper()

        # Infer from experience count in resume
        exp_count = len(candidate.resume_profile.experience)
        if exp_count == 0:
            return "INTERNSHIP"
        elif exp_count <= 2:
            return "ENTRY_LEVEL"
        elif exp_count <= 4:
            return "MID_LEVEL"
        else:
            return "SENIOR_LEVEL"

    @classmethod
    def evaluate(cls, candidate: CandidateProfile, job: JobPosting) -> ExperienceMatchEvaluation:
        candidate_level = cls._get_candidate_level(candidate)
        job_level = (job.experience_level or "").upper()

        if not job_level or job_level not in LEVEL_HIERARCHY:
            return ExperienceMatchEvaluation(
                score=85.0,
                candidate_level=candidate_level,
                job_level="NOT_SPECIFIED",
                reason="Job does not specify strict experience requirement; suitable for candidate.",
            )

        cand_rank = LEVEL_HIERARCHY.get(candidate_level, 2)
        job_rank = LEVEL_HIERARCHY.get(job_level, 2)
        diff = abs(cand_rank - job_rank)

        if diff == 0:
            score = 100.0
            reason = f"Experience level perfectly aligned ({candidate_level})."
        elif diff == 1:
            score = 80.0
            reason = f"Experience level is reasonably compatible ({candidate_level} vs {job_level})."
        elif diff == 2:
            score = 55.0
            reason = f"Moderate experience gap ({candidate_level} vs {job_level})."
        else:
            score = 30.0
            reason = f"Significant experience level disparity ({candidate_level} vs {job_level})."

        return ExperienceMatchEvaluation(
            score=score,
            candidate_level=candidate_level,
            job_level=job_level,
            reason=reason,
        )
