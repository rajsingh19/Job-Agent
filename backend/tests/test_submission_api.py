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
async def seed_api_app(db_session: AsyncSession):
    user_id = "user_api_test_01"
    pref = UserPreference(
        user_id=user_id,
        target_roles=["Backend Lead"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=150000.0,
    )
    db_session.add(pref)

    resume = Resume(
        id="res_api_test",
        user_id=user_id,
        name="resume.pdf",
        file_reference="user_api_test_01/resume.pdf",
        content_hash="hash_api_test",
        is_default=True,
        parsed_profile={
            "name": "API Candidate",
            "email": "api.cand@example.com",
            "phone": "+1-555-666-7777",
            "skills": ["Python", "FastAPI"],
        },
    )
    db_session.add(resume)

    job = JobPosting(
        id="job_api_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_api_1",
        title="Backend Lead",
        company="ApiCorp",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="RESTful API service lead.",
        skills=["Python"],
        apply_url="https://boards.greenhouse.io/apicorp/1",
        source_hash="sha_apicorp_1",
        is_active=True,
    )
    db_session.add(job)
    await db_session.commit()

    service = ApplicationDraftService()
    draft = await service.create_draft(
        db=db_session,
        user_id=user_id,
        job_id="job_api_01",
        include_cover_letter=True,
    )
    return user_id, draft.id


@pytest.mark.asyncio
async def test_api_approval_lifecycle(client: AsyncClient, seed_api_app):
    user_id, app_id = seed_api_app
    headers = {"X-User-Id": user_id}

    # 1. Attempt to approve without confirmation checkbox -> 400
    res = await client.post(
        f"/api/v1/applications/{app_id}/approve",
        headers=headers,
        json={"confirmation_checked": False, "user_notes": "test"},
    )
    assert res.status_code == 400

    # 2. Approve with confirmation -> 200 OK
    res = await client.post(
        f"/api/v1/applications/{app_id}/approve",
        headers=headers,
        json={"confirmation_checked": True, "user_notes": "Ready to submit"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["approved"] is True
    assert data["status"] == "APPROVED"
    assert "appr_" in data["approval_token"]
    assert len(data["approved_version_hash"]) == 64

    # 3. GET active approval status -> 200 OK
    res = await client.get(f"/api/v1/applications/{app_id}/approval", headers=headers)
    assert res.status_code == 200
    assert res.json()["approved"] is True

    # 4. Revoke approval -> 200 OK
    res = await client.post(
        f"/api/v1/applications/{app_id}/revoke-approval",
        headers=headers,
        json={"reason": "Need revision"},
    )
    assert res.status_code == 200
    assert res.json()["revoked"] is True

    # 5. GET active approval after revoke -> 404 NOT FOUND
    res = await client.get(f"/api/v1/applications/{app_id}/approval", headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_submission_guard_rejection(client: AsyncClient, seed_api_app):
    user_id, app_id = seed_api_app
    headers = {"X-User-Id": user_id}

    # Attempting to submit when not approved must return 403 FORBIDDEN
    res = await client.post(
        f"/api/v1/applications/{app_id}/submit",
        headers=headers,
        json={"approval_token": None},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "APPROVAL_REQUIRED"


@pytest.mark.asyncio
async def test_api_audit_trail_and_submission_status(client: AsyncClient, seed_api_app):
    user_id, app_id = seed_api_app
    headers = {"X-User-Id": user_id}

    # Approve
    await client.post(
        f"/api/v1/applications/{app_id}/approve",
        headers=headers,
        json={"confirmation_checked": True},
    )

    # Check Audit Log
    res = await client.get(f"/api/v1/applications/{app_id}/audit", headers=headers)
    assert res.status_code == 200
    events = res.json()
    assert isinstance(events, list)
    assert len(events) >= 2  # VALIDATION_PASSED, APPROVED

    # Check Submission status
    res = await client.get(f"/api/v1/applications/{app_id}/submission", headers=headers)
    assert res.status_code == 200
    assert res.json()["application_id"] == app_id
    assert res.json()["status"] == "APPROVED"
