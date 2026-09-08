import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService


@pytest_asyncio.fixture
async def seed_multi_user_drafts(db_session: AsyncSession):
    # User Alpha
    pref_a = UserPreference(
        user_id="user_alpha_sec",
        target_roles=["Backend Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=100000.0,
    )
    db_session.add(pref_a)

    resume_a = Resume(
        id="res_alpha_sec",
        user_id="user_alpha_sec",
        name="alpha_resume.pdf",
        file_reference="user_alpha_sec/resumes/alpha.pdf",
        content_hash="hash_alpha_sec",
        parsed_profile={"name": "Alpha User", "email": "alpha@example.com", "phone": "+1-555-0101", "skills": ["Python"]},
    )
    db_session.add(resume_a)

    # User Beta
    pref_b = UserPreference(
        user_id="user_beta_sec",
        target_roles=["Frontend Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=90000.0,
    )
    db_session.add(pref_b)

    resume_b = Resume(
        id="res_beta_sec",
        user_id="user_beta_sec",
        name="beta_resume.pdf",
        file_reference="user_beta_sec/resumes/beta.pdf",
        content_hash="hash_beta_sec",
        parsed_profile={"name": "Beta User", "email": "beta@example.com", "phone": "+1-555-0202", "skills": ["React"]},
    )
    db_session.add(resume_b)

    # Job
    job = JobPosting(
        id="job_sec_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_sec_01",
        title="Full Stack Engineer",
        company="GlobalTech",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Full stack software engineering with Python and React.",
        skills=["Python", "React"],
        apply_url="https://boards.greenhouse.io/globaltech/jobs/1",
        source_hash="sha_sec_01",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    # Create draft for User Alpha
    service = ApplicationDraftService()
    draft_alpha = await service.create_draft(
        db=db_session,
        user_id="user_alpha_sec",
        job_id="job_sec_01",
    )

    return draft_alpha.id


@pytest.mark.asyncio
async def test_create_and_get_draft_api_endpoints(client: AsyncClient, seed_multi_user_drafts):
    alpha_draft_id = seed_multi_user_drafts
    headers_alpha = {"X-User-Id": "user_alpha_sec"}

    # 1. Get Alpha's draft via API
    res_get = await client.get(f"/api/v1/applications/{alpha_draft_id}/draft", headers=headers_alpha)
    assert res_get.status_code == 200
    draft_data = res_get.json()
    assert draft_data["id"] == alpha_draft_id
    assert draft_data["user_id"] == "user_alpha_sec"

    # 2. Validate Alpha's draft via API
    res_val = await client.post(f"/api/v1/applications/{alpha_draft_id}/validate", headers=headers_alpha)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["application_id"] == alpha_draft_id
    assert val_data["is_valid"] is True

    # 3. Get Alpha's review package via API
    res_rev = await client.get(f"/api/v1/applications/{alpha_draft_id}/review", headers=headers_alpha)
    assert res_rev.status_code == 200
    rev_data = res_rev.json()
    assert rev_data["application_id"] == alpha_draft_id
    assert rev_data["job"]["title"] == "Full Stack Engineer"


@pytest.mark.asyncio
async def test_multi_user_draft_isolation(client: AsyncClient, seed_multi_user_drafts):
    """
    Verifies that User Beta CANNOT retrieve, validate, or inspect User Alpha's
    application draft or review package.
    """
    alpha_draft_id = seed_multi_user_drafts
    headers_beta = {"X-User-Id": "user_beta_sec"}

    # User Beta tries to get Alpha's draft -> 404 (or 403)
    res_get = await client.get(f"/api/v1/applications/{alpha_draft_id}/draft", headers=headers_beta)
    assert res_get.status_code in {404, 403}

    # User Beta tries to validate Alpha's draft -> 404 (or 403)
    res_val = await client.post(f"/api/v1/applications/{alpha_draft_id}/validate", headers=headers_beta)
    assert res_val.status_code in {404, 403}

    # User Beta tries to get Alpha's review package -> 404 (or 403)
    res_rev = await client.get(f"/api/v1/applications/{alpha_draft_id}/review", headers=headers_beta)
    assert res_rev.status_code in {404, 403}


@pytest.mark.asyncio
async def test_create_draft_via_jobs_endpoint(client: AsyncClient, seed_multi_user_drafts):
    headers_beta = {"X-User-Id": "user_beta_sec"}

    payload = {
        "include_cover_letter": True,
        "custom_questions": [
            {"question_id": "q1", "question": "Why do you want to work here?"}
        ],
    }
    res = await client.post("/api/v1/jobs/job_sec_01/application-draft", json=payload, headers=headers_beta)
    assert res.status_code == 200
    data = res.json()

    assert data["job_id"] == "job_sec_01"
    assert data["user_id"] == "user_beta_sec"
    assert data["resume_id"] == "res_beta_sec"
    assert len(data["fields"]) >= 5
    assert len(data["custom_questions"]) == 1
