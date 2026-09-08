import pytest
from app.models.job import JobPosting
from app.schemas.resume import (
    CandidateProfile,
    ExperienceItem,
    ProjectItem,
    ResumeProfile,
)
from app.services.matching.keyword_matcher import KeywordMatcher


def test_keyword_matching_exact_and_synonyms():
    candidate = CandidateProfile(
        user_id="user_kw_1",
        resume_profile=ResumeProfile(
            name="Alice",
            skills=["Python", "JS", "Postgres", "Docker"],
            experience=[
                ExperienceItem(
                    company="Alpha Co",
                    role="Dev",
                    skills_used=["FastAPI", "k8s"],
                )
            ],
            projects=[
                ProjectItem(
                    name="AI Search",
                    tech_stack=["TypeScript", "React.js"],
                )
            ],
        ),
        preferences={"required_skills": ["SQL"]},
    )

    job = JobPosting(
        source="GREENHOUSE",
        company="TechCorp",
        title="Full Stack Developer",
        description="We need JavaScript, PostgreSQL, Kubernetes, and Docker skills.",
        skills=["JavaScript", "PostgreSQL", "Kubernetes", "Docker", "AWS"],
        apply_url="https://jobs.example.com/1",
        source_hash="hash_1",
    )

    eval_result = KeywordMatcher.evaluate(candidate, job)

    assert "JavaScript" in eval_result.matched_skills
    assert "PostgreSQL" in eval_result.matched_skills
    assert "Kubernetes" in eval_result.matched_skills
    assert "Docker" in eval_result.matched_skills
    assert "AWS" in eval_result.missing_skills
    assert eval_result.score >= 75.0


def test_keyword_matcher_false_positive_prevention():
    """Verifies that single-letter skills like 'C' do not false-match 'C++' or 'CSS'."""
    candidate = CandidateProfile(
        user_id="user_kw_2",
        resume_profile=ResumeProfile(
            name="Bob",
            skills=["C"],  # Candidate only knows pure C
        ),
        preferences={},
    )

    job = JobPosting(
        source="LEVER",
        company="GameStudio",
        title="Engine Developer",
        description="Looking for C++ and CSS developers.",
        skills=["C++", "CSS"],
        apply_url="https://jobs.example.com/2",
        source_hash="hash_2",
    )

    eval_result = KeywordMatcher.evaluate(candidate, job)

    assert "C++" in eval_result.missing_skills
    assert "CSS" in eval_result.missing_skills
    assert len(eval_result.matched_skills) == 0
    assert eval_result.score == 0.0
