import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume


@pytest_asyncio.fixture
async def seed_jobs_and_users(db_session: AsyncSession):
    # Create Preferences for User Alpha
    pref_alpha = UserPreference(
        user_id="user_alpha_matching",
        target_roles=["Senior Python Engineer", "Backend Lead"],
        preferred_locations=["San Francisco, CA", "Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=120000.0,
        excluded_companies=["ToxicCorp"],
    )
    db_session.add(pref_alpha)

    # Create Parsed Resume for User Alpha
    resume_alpha = Resume(
        id="resume_alpha_id",
        user_id="user_alpha_matching",
        name="alpha_resume.pdf",
        file_reference="user_alpha_matching/resumes/alpha_resume.pdf",
        content_hash="hash_alpha_match",
        is_default=True,
        parsed_profile={
            "name": "Alpha Developer",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Redis", "AWS"],
            "experience": [
                {
                    "company": "Tech Innovations",
                    "role": "Senior Software Engineer",
                    "description": "Led backend microservices architecture using Python, FastAPI, and AWS.",
                }
            ],
            "confidence_score": 0.95,
        },
    )
    db_session.add(resume_alpha)

    # Create Preferences for User Beta (Chef / Hospitality)
    pref_beta = UserPreference(
        user_id="user_beta_matching",
        target_roles=["Executive Chef"],
        preferred_locations=["New York, NY"],
        remote_preference=RemoteType.ON_SITE.value,
        minimum_stipend=80000.0,
        excluded_companies=[],
    )
    db_session.add(pref_beta)

    resume_beta = Resume(
        id="resume_beta_id",
        user_id="user_beta_matching",
        name="beta_resume.pdf",
        file_reference="user_beta_matching/resumes/beta_resume.pdf",
        content_hash="hash_beta_match",
        is_default=True,
        parsed_profile={
            "name": "Beta Chef",
            "skills": ["Culinary Arts", "Kitchen Management", "Menu Design", "Food Safety"],
            "experience": [
                {
                    "company": "Fine Dining NYC",
                    "role": "Sous Chef",
                    "description": "Managed kitchen operations and culinary quality.",
                }
            ],
            "confidence_score": 0.90,
        },
    )
    db_session.add(resume_beta)

    # Seed Jobs
    job_swe = JobPosting(
        id="job_swe_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_swe_01",
        title="Senior Python Engineer",
        company="Fintech Giants",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        stipend_min=130000.0,
        stipend_max=160000.0,
        stipend_currency="USD",
        description="Looking for a Senior Python Engineer with FastAPI, PostgreSQL, and AWS experience.",
        skills=["Python", "FastAPI", "PostgreSQL", "AWS"],
        apply_url="https://fintech.example.com/apply/swe",
        source_hash="sha_swe_01",
        is_active=True,
    )
    db_session.add(job_swe)

    job_toxic = JobPosting(
        id="job_toxic_02",
        source="LEVER",
        source_type=JobSourceType.API.value,
        external_id="lev_02",
        title="Senior Backend Engineer",
        company="ToxicCorp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        stipend_min=150000.0,
        stipend_max=180000.0,
        stipend_currency="USD",
        description="Backend development with Python and Redis.",
        skills=["Python", "Redis"],
        apply_url="https://toxic.example.com/apply",
        source_hash="sha_toxic_02",
        is_active=True,
    )
    db_session.add(job_toxic)

    job_culinary = JobPosting(
        id="job_culinary_03",
        source="ASHBY",
        source_type=JobSourceType.API.value,
        external_id="ashby_03",
        title="Executive Chef",
        company="Grand Hotel NYC",
        location="New York, NY",
        remote_type=RemoteType.ON_SITE.value,
        stipend_min=90000.0,
        stipend_max=110000.0,
        stipend_currency="USD",
        description="Seeking an Executive Chef to lead fine dining culinary operations.",
        skills=["Culinary Arts", "Kitchen Management", "Menu Design"],
        apply_url="https://grandhotel.example.com/apply/chef",
        source_hash="sha_culinary_03",
        is_active=True,
    )
    db_session.add(job_culinary)

    await db_session.commit()


@pytest.mark.asyncio
async def test_match_single_job_api(client: AsyncClient, seed_jobs_and_users):
    headers = {"X-User-Id": "user_alpha_matching"}

    # 1. Match job_swe_01 (High match for Alpha)
    response = await client.post("/api/v1/jobs/job_swe_01/match", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["job_id"] == "job_swe_01"
    assert data["candidate_id"] == "user_alpha_matching"
    assert data["is_hard_match"] is True
    assert data["match_score"] >= 75.0
    assert "Python" in data["matched_skills"]
    assert "FastAPI" in data["matched_skills"]
    assert data["confidence"] >= 0.70

    # 2. Match job_toxic_02 (Hard filter fail due to excluded company)
    response_toxic = await client.post("/api/v1/jobs/job_toxic_02/match", headers=headers)
    assert response_toxic.status_code == 200
    data_toxic = response_toxic.json()

    assert data_toxic["job_id"] == "job_toxic_02"
    assert data_toxic["is_hard_match"] is False
    assert "excluded_company" in data_toxic["hard_filter_result"]["failed_constraints"]

    # 3. Match non-existent job -> 404
    response_404 = await client.post("/api/v1/jobs/non_existent_id/match", headers=headers)
    assert response_404.status_code == 404
    assert response_404.json()["detail"]["error"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_match_multiple_jobs_api(client: AsyncClient, seed_jobs_and_users):
    headers = {"X-User-Id": "user_alpha_matching"}

    payload = {
        "min_score": 0.0,
        "hard_match_only": False,
    }
    response = await client.post("/api/v1/jobs/match", json=payload, headers=headers)
    assert response.status_code == 200
    results = response.json()

    assert len(results) >= 3
    # Top result should be the Senior Python Engineer
    assert results[0]["job_id"] == "job_swe_01"
    assert results[0]["is_hard_match"] is True


@pytest.mark.asyncio
async def test_ranked_jobs_api_with_filters_and_pagination(client: AsyncClient, seed_jobs_and_users):
    headers = {"X-User-Id": "user_alpha_matching"}

    # 1. Fetch ranked jobs with hard_match_only=True
    res_hard = await client.get("/api/v1/jobs/ranked?hard_match_only=true", headers=headers)
    assert res_hard.status_code == 200
    data_hard = res_hard.json()

    assert data_hard["candidate_id"] == "user_alpha_matching"
    assert all(r["is_hard_match"] is True for r in data_hard["results"])
    # ToxicCorp should not be in the hard_match_only results
    job_ids = [r["job_id"] for r in data_hard["results"]]
    assert "job_toxic_02" not in job_ids

    # 2. Fetch with min_score filter
    res_score = await client.get("/api/v1/jobs/ranked?min_score=70.0", headers=headers)
    assert res_score.status_code == 200
    data_score = res_score.json()
    assert all(r["match_score"] >= 70.0 for r in data_score["results"])

    # 3. Pagination limit & offset
    res_pag = await client.get("/api/v1/jobs/ranked?limit=1&offset=0", headers=headers)
    assert res_pag.status_code == 200
    data_pag = res_pag.json()
    assert len(data_pag["results"]) == 1


@pytest.mark.asyncio
async def test_user_isolation_matching_profiles(client: AsyncClient, seed_jobs_and_users):
    """
    Verifies that User Alpha (Software Engineer) and User Beta (Chef) receive
    strictly isolated, candidate-specific scores and matching evaluations.
    """
    headers_alpha = {"X-User-Id": "user_alpha_matching"}
    headers_beta = {"X-User-Id": "user_beta_matching"}

    # 1. Match culinary job for Alpha vs Beta
    res_alpha_chef = await client.post("/api/v1/jobs/job_culinary_03/match", headers=headers_alpha)
    res_beta_chef = await client.post("/api/v1/jobs/job_culinary_03/match", headers=headers_beta)

    assert res_alpha_chef.status_code == 200
    assert res_beta_chef.status_code == 200

    match_alpha = res_alpha_chef.json()
    match_beta = res_beta_chef.json()

    # Beta is a chef -> high score, hard match PASS
    assert match_beta["is_hard_match"] is True
    assert match_beta["match_score"] >= 75.0
    assert "Culinary Arts" in match_beta["matched_skills"]

    # Alpha is a software dev -> low score for chef job
    assert match_alpha["match_score"] < match_beta["match_score"]
    assert len(match_alpha["matched_skills"]) == 0
