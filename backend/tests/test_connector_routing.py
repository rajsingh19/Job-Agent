import pytest
from app.models.job import JobPosting
from app.schemas.connector import ApplicationMethod, PlatformType
from app.services.connectors.router import ConnectorRouter


@pytest.fixture
def router() -> ConnectorRouter:
    return ConnectorRouter()


@pytest.mark.asyncio
async def test_route_greenhouse_job(router: ConnectorRouter):
    job = JobPosting(
        id="job_gh_route_1",
        source="GREENHOUSE",
        company="Canonical",
        title="Python Backend Engineer",
        description="Developing Ubuntu backend services",
        apply_url="https://boards.greenhouse.io/canonical/jobs/12345",
        source_hash="gh_route_1",
    )
    route = await router.route_job(job)

    assert route.job_id == "job_gh_route_1"
    assert route.platform == PlatformType.GREENHOUSE
    assert route.connector == "Greenhouse ATS Connector"
    assert route.application_method == ApplicationMethod.ATS
    assert route.requires_browser is False
    assert route.requires_login is False
    assert route.requires_user_action is False
    assert route.capabilities.can_submit_application is False


@pytest.mark.asyncio
async def test_route_lever_job(router: ConnectorRouter):
    job = JobPosting(
        id="job_lev_route_1",
        source="LEVER",
        company="Affirm",
        title="Staff Engineer",
        description="Fintech platform",
        apply_url="https://jobs.lever.co/affirm/5678",
        source_hash="lev_route_1",
    )
    route = await router.route_job(job)

    assert route.job_id == "job_lev_route_1"
    assert route.platform == PlatformType.LEVER
    assert route.connector == "Lever ATS Connector"
    assert route.application_method == ApplicationMethod.ATS
    assert route.requires_browser is False


@pytest.mark.asyncio
async def test_route_ashby_job(router: ConnectorRouter):
    job = JobPosting(
        id="job_ash_route_1",
        source="ASHBY",
        company="Cursor",
        title="AI Engineer",
        description="Next gen code editor",
        apply_url="https://jobs.ashbyhq.com/cursor/890",
        source_hash="ash_route_1",
    )
    route = await router.route_job(job)

    assert route.job_id == "job_ash_route_1"
    assert route.platform == PlatformType.ASHBY
    assert route.connector == "Ashby ATS Connector"
    assert route.application_method == ApplicationMethod.ATS
    assert route.requires_browser is False


@pytest.mark.asyncio
async def test_route_job_board_to_browser_and_login_requirement(router: ConnectorRouter):
    job = JobPosting(
        id="job_linkedin_route_1",
        source="GENERIC_BROWSER",
        company="LinkedIn Corp",
        title="Product Manager",
        description="Product strategy",
        apply_url="https://www.linkedin.com/jobs/view/9999",
        source_hash="li_route_1",
    )
    route = await router.route_job(job)

    assert route.platform == PlatformType.LINKEDIN
    assert route.connector == "Generic Browser Connector"
    assert route.application_method == ApplicationMethod.BROWSER
    assert route.requires_browser is True
    assert route.requires_login is True
    assert route.requires_user_action is False


@pytest.mark.asyncio
async def test_route_unknown_job_to_user_action(router: ConnectorRouter):
    job = JobPosting(
        id="job_unknown_route_1",
        source="UNKNOWN",
        company="Anonymous",
        title="Secret Agent",
        description="Classified",
        apply_url="",
        source_hash="unk_route_1",
    )
    route = await router.route_job(job)

    assert route.platform == PlatformType.UNKNOWN
    assert route.application_method == ApplicationMethod.USER_ACTION
    assert route.requires_user_action is True
    assert len(route.warnings) > 0


@pytest.mark.asyncio
async def test_batch_job_routing(router: ConnectorRouter):
    jobs = [
        JobPosting(
            id=f"batch_job_{i}",
            source="GREENHOUSE",
            company=f"Company {i}",
            title=f"Engineer {i}",
            description="Coding",
            apply_url=f"https://boards.greenhouse.io/co{i}/jobs/{i}",
            source_hash=f"batch_hash_{i}",
        )
        for i in range(3)
    ]
    routes = await router.route_jobs(jobs)
    assert len(routes) == 3
    assert all(r.platform == PlatformType.GREENHOUSE for r in routes)
