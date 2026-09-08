import httpx
import pytest
from app.models.enums import ATSProvider, JobSourceType, RemoteType
from app.schemas.job import JobSearchQuery
from app.services.discovery.sources.ashby import AshbySource
from app.services.discovery.sources.greenhouse import GreenhouseSource
from app.services.discovery.sources.lever import LeverSource


@pytest.mark.asyncio
async def test_greenhouse_source_success(monkeypatch):
    sample_response = {
        "jobs": [
            {
                "id": 101,
                "title": "Backend Software Engineer",
                "location": {"name": "San Francisco, CA"},
                "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/101",
                "content": "<p>We are seeking a Python developer with FastAPI expertise.</p>",
                "departments": [{"name": "Core Engineering"}],
            }
        ]
    }

    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=sample_response, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    source = GreenhouseSource(company_slugs=["gitlab"])
    query = JobSearchQuery(keywords=["Python"], limit=10)
    jobs = await source.search_jobs(query)

    assert len(jobs) == 1
    assert jobs[0].title == "Backend Software Engineer"
    assert jobs[0].company == "Gitlab"
    assert jobs[0].ats_provider == ATSProvider.GREENHOUSE
    assert "Python" in jobs[0].skills


@pytest.mark.asyncio
async def test_greenhouse_source_error_handling(monkeypatch):
    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(404, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    source = GreenhouseSource(company_slugs=["nonexistent_co"])
    query = JobSearchQuery(limit=10)
    jobs = await source.search_jobs(query)

    assert len(jobs) == 0


@pytest.mark.asyncio
async def test_lever_source_success(monkeypatch):
    sample_response = [
        {
            "id": "lever_202",
            "text": "Full Stack Engineer",
            "categories": {"location": "Remote"},
            "descriptionPlain": "Develop web applications using TypeScript and React.",
            "hostedUrl": "https://jobs.lever.co/palantir/lever_202",
            "applyUrl": "https://jobs.lever.co/palantir/lever_202/apply",
        }
    ]

    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=sample_response, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    source = LeverSource(company_slugs=["palantir"])
    query = JobSearchQuery(limit=10)
    jobs = await source.search_jobs(query)

    assert len(jobs) == 1
    assert jobs[0].title == "Full Stack Engineer"
    assert jobs[0].company == "Palantir"
    assert jobs[0].remote_type == RemoteType.REMOTE
    assert jobs[0].ats_provider == ATSProvider.LEVER


@pytest.mark.asyncio
async def test_ashby_source_success(monkeypatch):
    sample_response = {
        "jobs": [
            {
                "id": "ashby_303",
                "title": "Machine Learning Engineer",
                "location": "New York, NY",
                "isRemote": True,
                "jobUrl": "https://jobs.ashbyhq.com/openai/ashby_303",
                "applyUrl": "https://jobs.ashbyhq.com/openai/ashby_303/application",
                "descriptionPlain": "Build frontier AI systems using PyTorch and Python.",
            }
        ]
    }

    async def mock_get(self, url, *args, **kwargs):
        return httpx.Response(200, json=sample_response, request=httpx.Request("GET", str(url)))

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    source = AshbySource(company_slugs=["openai"])
    query = JobSearchQuery(limit=10)
    jobs = await source.search_jobs(query)

    assert len(jobs) == 1
    assert jobs[0].title == "Machine Learning Engineer"
    assert jobs[0].company == "Openai"
    assert jobs[0].ats_provider == ATSProvider.ASHBY
    assert jobs[0].remote_type == RemoteType.REMOTE
