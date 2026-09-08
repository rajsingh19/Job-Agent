import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import ATSProvider, JobSourceType, RemoteType
from app.schemas.job import JobPostingCreate, JobSearchQuery
from app.services.discovery.registry import JobSourceRegistry
from app.services.discovery.service import JobDiscoveryService
from app.services.discovery.sources.base import JobSource


class MockFailingSource(JobSource):
    def __init__(self):
        super().__init__(name="FailingSource", source_type=JobSourceType.API)

    async def search_jobs(self, query: JobSearchQuery) -> list[JobPostingCreate]:
        raise RuntimeError("Simulated external API 500 failure")


class MockSuccessfulSource(JobSource):
    def __init__(self):
        super().__init__(name="SuccessfulSource", source_type=JobSourceType.API)

    async def search_jobs(self, query: JobSearchQuery) -> list[JobPostingCreate]:
        return [
            JobPostingCreate(
                source="SuccessfulSource",
                source_type=JobSourceType.API,
                external_id="mock_101",
                title="AI Research Engineer",
                company="Nexus AI",
                location="San Francisco, CA",
                remote_type=RemoteType.HYBRID,
                description="Developing multi-agent systems with Python and PyTorch.",
                skills=["Python", "PyTorch", "LLM"],
                apply_url="https://nexus.ai/jobs/101",
                source_hash="sha256_mock_101",
            )
        ]


@pytest.mark.asyncio
async def test_discovery_service_failure_isolation_and_persistence(db_session: AsyncSession):
    registry = JobSourceRegistry()
    registry.register(MockFailingSource())
    registry.register(MockSuccessfulSource())

    service = JobDiscoveryService(registry=registry)
    query = JobSearchQuery(keywords=["AI"], limit=10)

    result = await service.discover_jobs(db=db_session, query=query)

    # Verifies that failing source did not crash the discovery run
    assert result.sources_attempted == 2
    assert result.sources_succeeded == 1
    assert len(result.source_errors) == 1
    assert result.source_errors[0].source == "FailingSource"

    # Verifies successful source was persisted
    assert result.total_unique == 1
    assert result.jobs[0].title == "AI Research Engineer"
    assert result.jobs[0].company == "Nexus AI"

    # Test idempotency: re-running does not duplicate DB rows
    re_run = await service.discover_jobs(db=db_session, query=query)
    assert re_run.total_unique == 1
    assert len(re_run.jobs) == 1


@pytest.mark.asyncio
async def test_job_discovery_api_endpoints(client: AsyncClient, monkeypatch):
    # Mock Greenhouse source inside discovery service endpoint
    sample_jobs = [
        JobPostingCreate(
            source="GREENHOUSE",
            source_type=JobSourceType.API,
            external_id="api_job_1",
            title="Senior Backend Engineer",
            company="CloudCorp",
            location="Remote",
            remote_type=RemoteType.REMOTE,
            description="High scale distributed systems with Python and FastAPI.",
            skills=["Python", "FastAPI", "PostgreSQL"],
            apply_url="https://boards.greenhouse.io/cloudcorp/jobs/1",
            source_hash="sha256_cloudcorp_1",
        )
    ]

    async def mock_search(self, query):
        return sample_jobs

    from app.services.discovery.sources.greenhouse import GreenhouseSource
    monkeypatch.setattr(GreenhouseSource, "search_jobs", mock_search)

    # 1. Trigger Discovery
    payload = {
        "keywords": ["Python"],
        "remote_type": "REMOTE",
        "limit": 10,
        "sources": ["Greenhouse"],
    }
    discover_res = await client.post("/api/v1/jobs/discover", json=payload)
    assert discover_res.status_code == 200
    disc_data = discover_res.json()
    assert disc_data["total_unique"] >= 1
    job_id = disc_data["jobs"][0]["id"]

    # 2. List Jobs via GET
    list_res = await client.get("/api/v1/jobs?limit=10")
    assert list_res.status_code == 200
    jobs_list = list_res.json()
    assert len(jobs_list) >= 1

    # 3. Get Single Job by ID
    get_res = await client.get(f"/api/v1/jobs/{job_id}")
    assert get_res.status_code == 200
    assert get_res.json()["company"] == "CloudCorp"
