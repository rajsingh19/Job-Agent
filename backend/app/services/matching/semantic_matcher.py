import logging
from typing import List, Optional
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile
from app.services.matching.embeddings.mock import MockEmbeddingGenerator
from app.services.matching.embeddings.provider import EmbeddingProvider
from app.services.matching.models import (
    SemanticMatchEvaluation,
    candidate_to_embedding_text,
    job_to_embedding_text,
)

logger = logging.getLogger(__name__)


class SemanticMatcher:
    """
    Computes vector semantic similarity between candidate profile and job posting
    with seamless fallback on embedding service unavailability.
    """

    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider

    @staticmethod
    def _cosine_to_score(cosine: float) -> float:
        """
        Converts cosine similarity (typically 0.3 - 0.9 for relevant texts)
        into a balanced 0–100 scale.
        """
        # Linear normalization mapping cosine range [0.0, 0.9] to [0, 100]
        score = max(0.0, min(100.0, (cosine / 0.85) * 100.0))
        return round(score, 1)

    async def evaluate(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
        candidate_vector: Optional[List[float]] = None,
    ) -> SemanticMatchEvaluation:
        try:
            # 1. Candidate vector (reused if provided)
            if candidate_vector is None:
                cand_text = candidate_to_embedding_text(candidate)
                candidate_vector = await self.embedding_provider.embed(cand_text)

            # 2. Job vector
            job_text = job_to_embedding_text(job)
            job_vector = await self.embedding_provider.embed(job_text)

            # 3. Cosine similarity
            cosine = MockEmbeddingGenerator.cosine_similarity(candidate_vector, job_vector)
            score = self._cosine_to_score(cosine)

            return SemanticMatchEvaluation(
                score=score,
                is_fallback=False,
                warning=None,
            )

        except Exception as e:
            logger.warning(f"Semantic embedding generation failed: {e}. Activating keyword-based fallback.")
            return SemanticMatchEvaluation(
                score=None,
                is_fallback=True,
                warning="Semantic embedding unavailable; keyword-based fallback used.",
            )
