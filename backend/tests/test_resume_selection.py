import pytest
from app.models.job import JobPosting
from app.models.resume import Resume
from app.schemas.resume import CandidateProfile, ResumeProfile
from app.services.applications.resume_selector import ResumeSelector


@pytest.fixture
def candidate_profile() -> CandidateProfile:
    return CandidateProfile(
        user_id="user_res_sel_1",
        resume_profile=ResumeProfile(
            name="Alex Dev",
            skills=["Python", "FastAPI", "PostgreSQL"],
        ),
        preferences={},
    )


@pytest.fixture
def job_posting() -> JobPosting:
    return JobPosting(
        id="job_python_lead",
        title="Senior Python Backend Engineer",
        company="Fintech Co",
        description="Looking for Python, FastAPI, and Docker expertise",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        apply_url="https://fintech.example.com/apply",
        source_hash="sha_py_lead_1",
    )


def test_resume_selection_single_resume(candidate_profile, job_posting):
    resume = Resume(
        id="res_01",
        user_id="user_res_sel_1",
        name="software_engineer.pdf",
        file_reference="user_res_sel_1/resumes/software_engineer.pdf",
        content_hash="hash_01",
        parsed_profile={"name": "Alex Dev", "skills": ["Python", "FastAPI"]},
    )

    result = ResumeSelector.select_resume(
        user_id="user_res_sel_1",
        candidate_profile=candidate_profile,
        job=job_posting,
        available_resumes=[resume],
    )

    assert result.resume_id == "res_01"
    assert result.confidence == 1.0
    assert result.requires_user_input is False


def test_resume_selection_multiple_resumes_best_match(candidate_profile, job_posting):
    # Resume 1: Python/Backend focused (High overlap with job)
    res_python = Resume(
        id="res_py_1",
        user_id="user_res_sel_1",
        name="python_backend_cv.pdf",
        file_reference="user_res_sel_1/resumes/py.pdf",
        content_hash="hash_py",
        parsed_profile={
            "name": "Alex Dev",
            "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
            "experience": [{"role": "Senior Python Engineer", "description": "Backend services"}],
        },
        is_default=True,
    )

    # Resume 2: Frontend focused (Low overlap with job)
    res_frontend = Resume(
        id="res_fe_2",
        user_id="user_res_sel_1",
        name="frontend_react_cv.pdf",
        file_reference="user_res_sel_1/resumes/fe.pdf",
        content_hash="hash_fe",
        parsed_profile={
            "name": "Alex Dev",
            "skills": ["React", "CSS", "HTML", "TypeScript"],
            "experience": [{"role": "Frontend Designer", "description": "UI styling"}],
        },
        is_default=False,
    )

    result = ResumeSelector.select_resume(
        user_id="user_res_sel_1",
        candidate_profile=candidate_profile,
        job=job_posting,
        available_resumes=[res_python, res_frontend],
    )

    assert result.resume_id == "res_py_1"
    assert result.requires_user_input is False
    assert result.match_score > 0.60


def test_resume_selection_ambiguous_flags_user_input(candidate_profile, job_posting):
    # Two resumes with virtually identical skills and experience
    res_a = Resume(
        id="res_a",
        user_id="user_res_sel_1",
        name="version_a.pdf",
        file_reference="path_a",
        content_hash="hash_a",
        parsed_profile={
            "name": "Alex",
            "skills": ["Python", "FastAPI"],
            "experience": [{"role": "Backend Developer", "description": "APIs"}],
        },
    )
    res_b = Resume(
        id="res_b",
        user_id="user_res_sel_1",
        name="version_b.pdf",
        file_reference="path_b",
        content_hash="hash_b",
        parsed_profile={
            "name": "Alex",
            "skills": ["Python", "FastAPI"],
            "experience": [{"role": "Backend Developer", "description": "APIs"}],
        },
    )

    result = ResumeSelector.select_resume(
        user_id="user_res_sel_1",
        candidate_profile=candidate_profile,
        job=job_posting,
        available_resumes=[res_a, res_b],
    )

    assert result.confidence <= 0.70
    assert result.requires_user_input is True
    assert "Ambiguous match" in result.selection_reason


def test_resume_selection_unauthorized_resume_error(candidate_profile, job_posting):
    resume_other_user = Resume(
        id="res_other",
        user_id="different_user",
        name="stolen_resume.pdf",
        file_reference="path",
        content_hash="hash_other",
    )

    with pytest.raises(ValueError, match="not found or unauthorized"):
        ResumeSelector.select_resume(
            user_id="user_res_sel_1",
            candidate_profile=candidate_profile,
            job=job_posting,
            available_resumes=[resume_other_user],
            requested_resume_id="res_other",
        )
