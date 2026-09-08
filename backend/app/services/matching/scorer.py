from typing import List, Optional, Tuple
from app.config.settings import Settings, get_settings
from app.models.job import JobPosting
from app.schemas.matching import HardFilterResult, JobMatchResult
from app.schemas.resume import CandidateProfile
from app.services.matching.models import (
    ExperienceMatchEvaluation,
    HardFilterEvaluation,
    RoleMatchEvaluation,
    SemanticMatchEvaluation,
    SkillMatchEvaluation,
)


class JobScorer:
    """
    Computes weighted match scores, dynamic fallback redistribution,
    deterministic explanations, and confidence metrics.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.w_keyword = self.settings.matching_keyword_weight
        self.w_semantic = self.settings.matching_semantic_weight
        self.w_role = self.settings.matching_role_weight
        self.w_experience = self.settings.matching_experience_weight
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = self.w_keyword + self.w_semantic + self.w_role + self.w_experience
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Matching weights must sum to 1.0 (currently {total:.3f}).")

    def calculate_match_score(
        self,
        keyword_score: float,
        semantic_score: Optional[float],
        role_score: float,
        experience_score: float,
    ) -> Tuple[float, bool]:
        """
        Calculates final composite 0-100 score.
        If semantic_score is None, redistributes its weight across remaining components.
        Returns: (final_score, is_fallback)
        """
        if semantic_score is not None:
            score = (
                keyword_score * self.w_keyword
                + semantic_score * self.w_semantic
                + role_score * self.w_role
                + experience_score * self.w_experience
            )
            return round(max(0.0, min(100.0, score)), 1), False
        else:
            # Semantic fallback: dynamically redistribute semantic weight
            remaining_weight = self.w_keyword + self.w_role + self.w_experience
            if remaining_weight <= 0:
                return round(keyword_score, 1), True

            scaled_k = self.w_keyword / remaining_weight
            scaled_r = self.w_role / remaining_weight
            scaled_e = self.w_experience / remaining_weight

            score = (
                keyword_score * scaled_k
                + role_score * scaled_r
                + experience_score * scaled_e
            )
            return round(max(0.0, min(100.0, score)), 1), True

    @staticmethod
    def calculate_confidence(
        candidate: CandidateProfile,
        job: JobPosting,
        is_semantic_fallback: bool,
        hard_filter: HardFilterEvaluation,
    ) -> Tuple[float, bool]:
        """
        Calculates a 0.0 - 1.0 confidence indicator based on data completeness
        and semantic availability.
        """
        confidence = 1.0
        low_confidence = False

        # Profile completeness
        prof = candidate.resume_profile
        if not prof.skills or len(prof.skills) < 3:
            confidence -= 0.15
        if not prof.experience and not prof.projects:
            confidence -= 0.15
        if prof.low_confidence:
            confidence -= 0.20
            low_confidence = True

        # Job completeness
        if not job.description or len(job.description) < 100:
            confidence -= 0.15
        if not job.skills:
            confidence -= 0.10

        # Semantic fallback penalty
        if is_semantic_fallback:
            confidence -= 0.20
            low_confidence = True

        # Unknown constraints
        if hard_filter.unknown_constraints:
            confidence -= 0.05 * len(hard_filter.unknown_constraints)

        confidence_val = round(max(0.2, min(1.0, confidence)), 2)
        if confidence_val < 0.65:
            low_confidence = True

        return confidence_val, low_confidence

    @staticmethod
    def build_explanation(
        match_score: float,
        hard_filter: HardFilterEvaluation,
        skill_eval: SkillMatchEvaluation,
        role_eval: RoleMatchEvaluation,
        exp_eval: ExperienceMatchEvaluation,
        is_semantic_fallback: bool,
    ) -> Tuple[str, List[str]]:
        """Synthesizes human-readable match explanation and bulleted reasons."""
        reasons: List[str] = []

        # 1. Role fit
        reasons.append(role_eval.similarity_reason)

        # 2. Skills fit
        if skill_eval.matched_skills:
            reasons.append(
                f"Matched {len(skill_eval.matched_skills)}/{skill_eval.total_job_skills} key skills ({', '.join(skill_eval.matched_skills[:5])})."
            )
        if skill_eval.missing_skills:
            reasons.append(
                f"Missing skills: {', '.join(skill_eval.missing_skills[:4])}."
            )

        # 3. Experience fit
        reasons.append(exp_eval.reason)

        # 4. Hard filter status
        if not hard_filter.passed:
            reasons.append(f"Hard constraint alerts: {', '.join(hard_filter.failed_constraints)}.")

        # Summary explanation paragraph
        level_str = "Strong" if match_score >= 80 else ("Moderate" if match_score >= 60 else "Weak")
        explanation = (
            f"{level_str} match ({match_score:.1f}%). {role_eval.similarity_reason} "
            f"Candidate matches {len(skill_eval.matched_skills)} key skill(s). "
            f"{exp_eval.reason}"
        )
        if is_semantic_fallback:
            explanation += " (Note: Scored via keyword fallback due to embedding unavailability)."

        return explanation, reasons
