import asyncio
import logging
from typing import List, Optional
from app.config.settings import Settings, get_settings
from app.models.job import JobPosting
from app.schemas.matching import HardFilterResult, JobMatchResult
from app.schemas.resume import CandidateProfile
from app.services.matching.embeddings.provider import EmbeddingProvider, get_embedding_provider
from app.services.matching.experience_matcher import ExperienceMatcher
from app.services.matching.hard_filters import HardFilterEngine
from app.services.matching.keyword_matcher import KeywordMatcher
from app.services.matching.models import candidate_to_embedding_text
from app.services.matching.role_matcher import RoleMatcher
from app.services.matching.scorer import JobScorer
from app.services.matching.semantic_matcher import SemanticMatcher

logger = logging.getLogger(__name__)


class JobMatchingService:
    """
    Coordinates end-to-end candidate-job matching, hard filtering,
    semantic embedding comparison, explainable scoring, and ranking.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self.settings = settings or get_settings()
        self.embedding_provider = embedding_provider or get_embedding_provider(self.settings)
        self.semantic_matcher = SemanticMatcher(self.embedding_provider)
        self.scorer = JobScorer(self.settings)

    async def match_job(
        self,
        candidate_profile: CandidateProfile,
        job: JobPosting,
        candidate_vector: Optional[List[float]] = None,
    ) -> JobMatchResult:
        """Evaluates a single job against candidate profile."""
        # 1. Hard Filter Evaluation
        hard_eval = HardFilterEngine.evaluate(candidate_profile, job)

        # 2. Keyword / Skill Match Evaluation
        skill_eval = KeywordMatcher.evaluate(candidate_profile, job)

        # 3. Semantic Embedding Match Evaluation
        sem_eval = await self.semantic_matcher.evaluate(
            candidate=candidate_profile,
            job=job,
            candidate_vector=candidate_vector,
        )

        # 4. Role Match Evaluation
        role_eval = RoleMatcher.evaluate(candidate_profile, job)

        # 5. Experience Match Evaluation
        exp_eval = ExperienceMatcher.evaluate(candidate_profile, job)

        # 6. Composite Score & Fallback Handling
        match_score, is_fallback = self.scorer.calculate_match_score(
            keyword_score=skill_eval.score,
            semantic_score=sem_eval.score,
            role_score=role_eval.score,
            experience_score=exp_eval.score,
        )

        # 7. Confidence Indicator
        confidence, low_confidence = self.scorer.calculate_confidence(
            candidate=candidate_profile,
            job=job,
            is_semantic_fallback=sem_eval.is_fallback,
            hard_filter=hard_eval,
        )

        # 8. Explanations & Reasons
        explanation, reasons = self.scorer.build_explanation(
            match_score=match_score,
            hard_filter=hard_eval,
            skill_eval=skill_eval,
            role_eval=role_eval,
            exp_eval=exp_eval,
            is_semantic_fallback=sem_eval.is_fallback,
        )

        warnings: List[str] = []
        if sem_eval.warning:
            warnings.append(sem_eval.warning)
        if not hard_eval.passed:
            warnings.extend([f"Hard constraint alert: {f}" for f in hard_eval.failed_constraints])

        return JobMatchResult(
            job_id=job.id,
            candidate_id=candidate_profile.user_id,
            job_title=job.title,
            company=job.company,
            is_hard_match=hard_eval.passed,
            match_score=match_score,
            hard_filter_result=HardFilterResult(
                passed=hard_eval.passed,
                failed_constraints=hard_eval.failed_constraints,
                unknown_constraints=hard_eval.unknown_constraints,
                details=hard_eval.details,
            ),
            matched_skills=skill_eval.matched_skills,
            missing_skills=skill_eval.missing_skills,
            keyword_score=skill_eval.score,
            semantic_score=sem_eval.score,
            role_score=role_eval.score,
            experience_score=exp_eval.score,
            explanation=explanation,
            confidence=confidence,
            low_confidence=low_confidence,
            reasons=reasons,
            warnings=warnings,
        )

    async def match_jobs(
        self,
        candidate_profile: CandidateProfile,
        jobs: List[JobPosting],
        min_score: float = 0.0,
        hard_match_only: bool = False,
    ) -> List[JobMatchResult]:
        """
        Matches multiple jobs against a candidate profile.
        Computes candidate embedding once and reuses it across all jobs.
        """
        if not jobs:
            return []

        # 1. Precompute candidate vector once
        cand_text = candidate_to_embedding_text(candidate_profile)
        candidate_vector: Optional[List[float]] = None
        try:
            candidate_vector = await self.embedding_provider.embed(cand_text)
        except Exception as e:
            logger.warning(f"Could not precompute candidate vector: {e}. Falling back to keyword scoring.")

        # 2. Evaluate all jobs concurrently
        tasks = [
            self.match_job(
                candidate_profile=candidate_profile,
                job=job,
                candidate_vector=candidate_vector,
            )
            for job in jobs
        ]
        results = await asyncio.gather(*tasks)

        # 3. Filter results
        filtered_results: List[JobMatchResult] = []
        for r in results:
            if hard_match_only and not r.is_hard_match:
                continue
            if r.match_score < min_score:
                continue
            filtered_results.append(r)

        # 4. Rank
        return self.rank_jobs(filtered_results)

    @staticmethod
    def rank_jobs(results: List[JobMatchResult]) -> List[JobMatchResult]:
        """
        Ranks matched jobs:
        1. Hard match pass (True before False)
        2. Match score descending
        3. Confidence descending
        4. Job ID tiebreaker
        """
        return sorted(
            results,
            key=lambda r: (
                1 if r.is_hard_match else 0,
                r.match_score,
                r.confidence,
                r.job_id,
            ),
            reverse=True,
        )
