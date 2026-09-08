import pytest
from app.models.enums import RemoteType
from app.models.job import JobPosting
from app.schemas.resume import CandidateProfile, ResumeProfile
from app.services.matching.hard_filters import HardFilterEngine


def make_candidate(
    preferred_locations=None,
    remote_preference="ANY",
    minimum_stipend=None,
    excluded_companies=None,
    target_roles=None,
) -> CandidateProfile:
    return CandidateProfile(
        user_id="test_candidate_1",
        resume_profile=ResumeProfile(
            name="Test Candidate",
            skills=["Python", "FastAPI"],
        ),
        preferences={
            "preferred_locations": preferred_locations or [],
            "remote_preference": remote_preference,
            "minimum_stipend": minimum_stipend,
            "excluded_companies": excluded_companies or [],
            "target_roles": target_roles or ["Backend Engineer"],
        },
    )


def make_job(
    company="TechCorp",
    title="Backend Engineer",
    location="San Francisco, CA",
    remote_type="REMOTE",
    stipend_min=None,
    stipend_max=None,
) -> JobPosting:
    return JobPosting(
        id="job_test_1",
        source="GREENHOUSE",
        company=company,
        title=title,
        location=location,
        remote_type=remote_type,
        stipend_min=stipend_min,
        stipend_max=stipend_max,
        description="Backend engineering role with Python and FastAPI.",
        apply_url="https://jobs.example.com/1",
        source_hash="hash_1",
    )


def test_hard_filter_pass_all_constraints():
    candidate = make_candidate(
        preferred_locations=["San Francisco"],
        remote_preference="REMOTE",
        minimum_stipend=80000.0,
        excluded_companies=["SpamCo"],
    )
    job = make_job(
        company="TechCorp",
        location="San Francisco, CA",
        remote_type="REMOTE",
        stipend_min=90000.0,
        stipend_max=120000.0,
    )

    eval_result = HardFilterEngine.evaluate(candidate, job)
    assert eval_result.passed is True
    assert len(eval_result.failed_constraints) == 0


def test_hard_filter_excluded_company():
    candidate = make_candidate(excluded_companies=["SpammyCorp Inc."])
    job = make_job(company="SpammyCorp")

    eval_result = HardFilterEngine.evaluate(candidate, job)
    assert eval_result.passed is False
    assert "excluded_company" in eval_result.failed_constraints


def test_hard_filter_remote_preference_mismatch():
    candidate = make_candidate(remote_preference="REMOTE")
    job = make_job(remote_type="ON_SITE", location="New York, NY")

    eval_result = HardFilterEngine.evaluate(candidate, job)
    assert eval_result.passed is False
    assert "remote_work_policy" in eval_result.failed_constraints


def test_hard_filter_location_mismatch():
    candidate = make_candidate(
        preferred_locations=["Bangalore"],
        remote_preference="ON_SITE",
    )
    job = make_job(
        location="Berlin, Germany",
        remote_type="ON_SITE",
    )

    eval_result = HardFilterEngine.evaluate(candidate, job)
    assert eval_result.passed is False
    assert "location" in eval_result.failed_constraints


def test_hard_filter_salary_unmet_and_unknown():
    candidate = make_candidate(minimum_stipend=100000.0)

    # Job max salary is below minimum
    job_low = make_job(stipend_min=50000.0, stipend_max=80000.0)
    res_low = HardFilterEngine.evaluate(candidate, job_low)
    assert res_low.passed is False
    assert "minimum_stipend" in res_low.failed_constraints

    # Job salary is unknown -> should NOT fail hard filter, but record in unknown_constraints
    job_unknown = make_job(stipend_min=None, stipend_max=None)
    res_unknown = HardFilterEngine.evaluate(candidate, job_unknown)
    assert res_unknown.passed is True
    assert "salary" in res_unknown.unknown_constraints
