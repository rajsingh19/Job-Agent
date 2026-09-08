import pytest
from app.models.job import JobPosting
from app.schemas.connector import PlatformType
from app.services.connectors.detector import ATSDetector


@pytest.fixture
def detector() -> ATSDetector:
    return ATSDetector()


def test_detect_greenhouse_urls(detector: ATSDetector):
    urls = [
        "https://boards.greenhouse.io/canonical/jobs/123456",
        "https://job-boards.greenhouse.io/cloudflare/jobs/789",
        "http://boards.greenhouse.io/embed/job_app?token=999",
    ]
    for url in urls:
        job = JobPosting(
            source="GREENHOUSE",
            company="Canonical",
            title="Software Engineer",
            description="Python engineer",
            apply_url=url,
            source_hash=f"gh_{hash(url)}",
        )
        res = detector.detect_platform(job)
        assert res.platform == PlatformType.GREENHOUSE
        assert res.confidence >= 0.90
        assert res.requires_browser is False
        assert any("greenhouse" in s for s in res.signals)


def test_detect_lever_urls(detector: ATSDetector):
    job = JobPosting(
        source="LEVER",
        company="Netflix",
        title="Backend Engineer",
        description="Distributed systems",
        apply_url="https://jobs.lever.co/netflix/abc-123",
        source_hash="lev_1",
    )
    res = detector.detect_platform(job)
    assert res.platform == PlatformType.LEVER
    assert res.confidence >= 0.90
    assert res.requires_browser is False


def test_detect_ashby_urls(detector: ATSDetector):
    job = JobPosting(
        source="ASHBY",
        company="OpenAI",
        title="Research Engineer",
        description="Frontier AI",
        apply_url="https://jobs.ashbyhq.com/openai/xyz-789",
        source_hash="ashby_1",
    )
    res = detector.detect_platform(job)
    assert res.platform == PlatformType.ASHBY
    assert res.confidence >= 0.90
    assert res.requires_browser is False


def test_detect_major_job_portals(detector: ATSDetector):
    portals = [
        ("https://www.linkedin.com/jobs/view/123456", PlatformType.LINKEDIN),
        ("https://internshala.com/internship/detail/python-intern-123", PlatformType.INTERNSHALA),
        ("https://www.naukri.com/job-listings-senior-developer-delhi-123", PlatformType.NAUKRI),
        ("https://www.shine.com/jobs/full-stack-engineer/123", PlatformType.SHINE),
        ("https://wellfound.com/company/startup/jobs/123", PlatformType.WELLFOUND),
    ]

    for url, expected_platform in portals:
        job = JobPosting(
            source="GENERIC_BROWSER",
            company="PortalCompany",
            title="Software Developer",
            description="Full stack",
            apply_url=url,
            source_hash=f"portal_{hash(url)}",
        )
        res = detector.detect_platform(job)
        assert res.platform == expected_platform
        assert res.confidence >= 0.90
        assert res.requires_browser is True


def test_detect_generic_ats_and_browser_fallback(detector: ATSDetector):
    # 1. Workday / Generic ATS
    job_workday = JobPosting(
        source="GENERIC_ATS",
        company="BigEnterprise",
        title="Lead Architect",
        description="Enterprise architecture",
        apply_url="https://bigenterprise.myworkdayjobs.com/en-US/careers/job/123",
        source_hash="wd_1",
    )
    res_wd = detector.detect_platform(job_workday)
    assert res_wd.platform == PlatformType.GENERIC_ATS
    assert res_wd.confidence >= 0.85
    assert res_wd.requires_browser is True

    # 2. Generic company career portal URL
    job_generic = JobPosting(
        source="BROWSER",
        company="Acme Corp",
        title="Frontend Developer",
        description="React developer",
        apply_url="https://acmecorp.example.com/careers/frontend",
        source_hash="acme_1",
    )
    res_gen = detector.detect_platform(job_generic)
    assert res_gen.platform == PlatformType.BROWSER
    assert res_gen.requires_browser is True

    # 3. Empty / Malformed URL -> Unknown
    job_unknown = JobPosting(
        source="UNKNOWN",
        company="Mystery Co",
        title="Unknown Job",
        description="No details",
        apply_url="",
        source_hash="unk_1",
    )
    res_unk = detector.detect_platform(job_unknown)
    assert res_unk.platform == PlatformType.UNKNOWN
    assert res_unk.confidence <= 0.50
    assert len(res_unk.warnings) > 0


def test_detect_conflicting_signals(detector: ATSDetector):
    """
    When metadata says Greenhouse but apply_url points to Lever,
    detector should prioritize apply_url, record warning, and lower confidence.
    """
    job = JobPosting(
        source="GREENHOUSE",  # Conflicting metadata
        company="Stripe",
        title="Software Engineer",
        description="Payments API",
        apply_url="https://jobs.lever.co/stripe/conflicting-id",
        source_hash="conflict_1",
    )
    res = detector.detect_platform(job)
    assert res.platform == PlatformType.LEVER
    assert any("Conflicting signals" in w for w in res.warnings)
    assert res.confidence < 0.90  # Lowered confidence due to conflict
    assert any("conflict=resolved_to_lever" in s for s in res.signals)
