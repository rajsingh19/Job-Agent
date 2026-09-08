import pytest
from app.config.settings import Settings
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile, ResumeProfile
from app.services.matching.models import (
    ExperienceMatchEvaluation,
    HardFilterEvaluation,
    RoleMatchEvaluation,
    SkillMatchEvaluation,
)
from app.services.matching.scorer import JobScorer


def test_scoring_weights_validation():
    # Valid weights (sum = 1.0)
    valid_settings = Settings(
        matching_keyword_weight=0.30,
        matching_semantic_weight=0.35,
        matching_role_weight=0.20,
        matching_experience_weight=0.15,
    )
    scorer = JobScorer(settings=valid_settings)
    assert scorer is not None

    # Invalid weights (sum != 1.0)
    invalid_settings = Settings(
        matching_keyword_weight=0.50,
        matching_semantic_weight=0.50,
        matching_role_weight=0.50,
        matching_experience_weight=0.50,
    )
    with pytest.raises(ValueError):
        JobScorer(settings=invalid_settings)


def test_score_calculation_and_semantic_fallback_redistribution():
    settings = Settings(
        matching_keyword_weight=0.30,
        matching_semantic_weight=0.40,
        matching_role_weight=0.20,
        matching_experience_weight=0.10,
    )
    scorer = JobScorer(settings=settings)

    # 1. Standard calculation with semantic score present
    # Score = 80*0.30 + 90*0.40 + 100*0.20 + 80*0.10 = 24 + 36 + 20 + 8 = 88.0
    score, is_fallback = scorer.calculate_match_score(
        keyword_score=80.0,
        semantic_score=90.0,
        role_score=100.0,
        experience_score=80.0,
    )
    assert score == 88.0
    assert is_fallback is False

    # 2. Semantic fallback calculation (semantic_score = None)
    # Remaining weights: 0.30 + 0.20 + 0.10 = 0.60
    # Scaled weights: kw = 0.30/0.60 = 0.50, role = 0.20/0.60 = 0.333, exp = 0.10/0.60 = 0.1667
    # Score = 80*0.50 + 100*(1/3) + 80*(1/6) = 40 + 33.33 + 13.33 = 86.7
    score_fb, is_fallback_fb = scorer.calculate_match_score(
        keyword_score=80.0,
        semantic_score=None,
        role_score=100.0,
        experience_score=80.0,
    )
    assert 86.0 <= score_fb <= 87.0
    assert is_fallback_fb is True


def test_confidence_and_explainability_generation():
    candidate = CandidateProfile(
        user_id="user_score_1",
        resume_profile=ResumeProfile(
            name="Charlie",
            skills=["Python", "FastAPI", "Docker", "SQL"],
        ),
        preferences={},
    )
    job = JobPosting(
        source="GREENHOUSE",
        company="DataCorp",
        title="Backend Developer",
        description="FastAPI role in San Francisco.",
        skills=["Python", "FastAPI", "Kubernetes"],
        apply_url="https://jobs.example.com/1",
        source_hash="hash_1",
    )

    hard_filter = HardFilterEvaluation(passed=True)
    confidence, low_confidence = JobScorer.calculate_confidence(
        candidate=candidate,
        job=job,
        is_semantic_fallback=False,
        hard_filter=hard_filter,
    )
    assert confidence >= 0.70
    assert low_confidence is False

    explanation, reasons = JobScorer.build_explanation(
        match_score=85.0,
        hard_filter=hard_filter,
        skill_eval=SkillMatchEvaluation(
            score=66.7,
            matched_skills=["Python", "FastAPI"],
            missing_skills=["Kubernetes"],
            total_job_skills=3,
        ),
        role_eval=RoleMatchEvaluation(score=100.0, similarity_reason="Exact role match with target."),
        exp_eval=ExperienceMatchEvaluation(score=100.0, reason="Experience level suitable."),
        is_semantic_fallback=False,
    )

    assert "Strong match (85.0%)" in explanation
    assert len(reasons) >= 3
    assert any("Python, FastAPI" in r for r in reasons)
