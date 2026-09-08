import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting


@pytest_asyncio.fixture
async def seed_test_jobs(db_session: AsyncSession):
    job_gh = JobPosting(
        id="sec_job_gh_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_sec_01",
        title="Security Engineer",
        company="GitLab",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Application security and penetration testing.",
        skills=["Python", "Security", "AppSec"],
        apply_url="https://boards.greenhouse.io/gitlab/jobs/sec_01",
        source_hash="sha_sec_gh_01",
        is_active=True,
    )
    db_session.add(job_gh)

    job_li = JobPosting(
        id="sec_job_li_02",
        source="GENERIC_BROWSER",
        source_type=JobSourceType.BROWSER.value,
        external_id="li_sec_02",
        title="Frontend Architect",
        company="StartupHub",
        location="San Francisco, CA",
        remote_type=RemoteType.HYBRID.value,
        description="Modern React and TypeScript UI.",
        skills=["React", "TypeScript"],
        apply_url="https://www.linkedin.com/jobs/view/sec_02",
        source_hash="sha_sec_li_02",
        is_active=True,
    )
    db_session.add(job_li)

    await db_session.commit()


@pytest.mark.asyncio
async def test_detect_platform_api(client: AsyncClient, seed_test_jobs):
    headers = {"X-User-Id": "user_sec_test"}

    # 1. Detect Greenhouse platform
    res_gh = await client.post("/api/v1/jobs/sec_job_gh_01/detect-platform", headers=headers)
    assert res_gh.status_code == 200
    data_gh = res_gh.json()

    assert data_gh["job_id"] == "sec_job_gh_01"
    assert data_gh["platform"] == "greenhouse"
    assert data_gh["application_method"] == "ats"
    assert data_gh["requires_browser"] is False
    assert data_gh["requires_user_action"] is False
    assert data_gh["confidence"] >= 0.90

    # 2. Detect LinkedIn platform
    res_li = await client.post("/api/v1/jobs/sec_job_li_02/detect-platform", headers=headers)
    assert res_li.status_code == 200
    data_li = res_li.json()

    assert data_li["job_id"] == "sec_job_li_02"
    assert data_li["platform"] == "linkedin"
    assert data_li["application_method"] == "browser"
    assert data_li["requires_browser"] is True

    # 3. 404 on non-existent job
    res_404 = await client.post("/api/v1/jobs/invalid_job_id/detect-platform", headers=headers)
    assert res_404.status_code == 404
    assert res_404.json()["detail"]["error"] == "JOB_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_application_route_api(client: AsyncClient, seed_test_jobs):
    headers = {"X-User-Id": "user_sec_test"}

    res = await client.get("/api/v1/jobs/sec_job_gh_01/application-route", headers=headers)
    assert res.status_code == 200
    route = res.json()

    assert route["job_id"] == "sec_job_gh_01"
    assert route["platform"] == "greenhouse"
    assert route["connector"] == "Greenhouse ATS Connector"
    assert route["application_method"] == "ats"
    # Verify capability reporting is honest
    assert route["capabilities"]["can_submit_application"] is False
    assert route["capabilities"]["can_fill_application"] is False

    # 404 for invalid job ID
    res_404 = await client.get("/api/v1/jobs/invalid_job_id/application-route", headers=headers)
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_list_connectors_api(client: AsyncClient):
    headers = {"X-User-Id": "user_sec_test"}

    res = await client.get("/api/v1/connectors", headers=headers)
    assert res.status_code == 200
    connectors = res.json()

    assert len(connectors) >= 4
    platform_names = [c["platform"] for c in connectors]
    assert "greenhouse" in platform_names
    assert "lever" in platform_names
    assert "ashby" in platform_names
    assert "browser" in platform_names

    # Verify no credentials or internal file paths leaked in connector definitions
    for c in connectors:
        assert "password" not in c
        assert "secret" not in c
        assert "token" not in c
        assert "api_key" not in c
