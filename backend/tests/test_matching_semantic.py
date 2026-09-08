import pytest
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile, ExperienceItem, ResumeProfile
from app.services.matching.embeddings.provider import MockEmbeddingProvider
from app.services.matching.semantic_matcher import SemanticMatcher


@pytest.mark.asyncio
async def test_semantic_matching_high_vs_low_similarity():
    provider = MockEmbeddingProvider()
    matcher = SemanticMatcher(embedding_provider=provider)

    candidate = CandidateProfile(
        user_id="user_sem_1",
        resume_profile=ResumeProfile(
            name="ML Engineer",
            skills=["Python", "PyTorch", "Machine Learning", "Transformers", "NLP"],
            experience=[
                ExperienceItem(
                    company="AI Labs",
                    role="AI Researcher",
                    description="Trained large language models with PyTorch and distributed clusters.",
                )
            ],
        ),
        preferences={"target_roles": ["Machine Learning Engineer", "AI Researcher"]},
    )

    # Relevant job
    job_relevant = JobPosting(
        source="ASHBY",
        company="OpenAI",
        title="Machine Learning Engineer",
        description="Developing frontier AI models with PyTorch, NLP, and distributed computing.",
        skills=["Python", "PyTorch", "NLP"],
        apply_url="https://openai.com/jobs/1",
        source_hash="hash_ml_1",
    )

    # Completely unrelated job
    job_unrelated = JobPosting(
        source="GREENHOUSE",
        company="HotelGroup",
        title="Executive Chef",
        description="Responsible for restaurant culinary operations, kitchen staff management, and menu design.",
        skills=["Culinary Arts", "Kitchen Management"],
        apply_url="https://hotels.example.com/chef",
        source_hash="hash_chef_1",
    )

    eval_relevant = await matcher.evaluate(candidate, job_relevant)
    eval_unrelated = await matcher.evaluate(candidate, job_unrelated)

    assert eval_relevant.score is not None
    assert eval_unrelated.score is not None
    assert eval_relevant.score > eval_unrelated.score
    assert eval_relevant.score >= 65.0
    assert eval_unrelated.score <= 30.0
    assert eval_relevant.is_fallback is False


@pytest.mark.asyncio
async def test_semantic_matcher_fallback_on_provider_outage():
    # Simulating outage in embedding provider
    failing_provider = MockEmbeddingProvider(should_fail=True)
    matcher = SemanticMatcher(embedding_provider=failing_provider)

    candidate = CandidateProfile(
        user_id="user_sem_2",
        resume_profile=ResumeProfile(name="Dev", skills=["Python"]),
        preferences={},
    )
    job = JobPosting(
        source="LEVER",
        company="StartupCo",
        title="Python Developer",
        description="FastAPI development",
        apply_url="https://jobs.example.com/1",
        source_hash="hash_2",
    )

    eval_result = await matcher.evaluate(candidate, job)

    assert eval_result.score is None
    assert eval_result.is_fallback is True
    assert "Semantic embedding unavailable" in eval_result.warning
