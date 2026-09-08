import pytest
from app.models.enums import JobSourceType, RemoteType
from app.schemas.job import JobSearchQuery
from app.services.discovery.sources.browser import (
    BrowserDiscoveryConfig,
    GenericBrowserDiscovery,
)

SAMPLE_HTML_PAGE = """
<!DOCTYPE html>
<html>
<head><title>Job Board</title></head>
<body>
    <div class="jobs-container">
        <div class="job-card">
            <h2 class="job-title">Software Developer (Remote)</h2>
            <span class="company-name">InnoTech Solutions Inc.</span>
            <div class="job-location">Remote</div>
            <a href="/jobs/dev-101">View Details</a>
            <p class="job-description">Looking for Python, FastAPI, and Docker developers.</p>
        </div>
        <div class="job-card">
            <h2 class="job-title">Frontend Intern</h2>
            <span class="company-name">DesignWorks</span>
            <div class="job-location">San Francisco, CA</div>
            <a href="/jobs/front-102">View Details</a>
            <p class="job-description">React and TypeScript internship.</p>
        </div>
    </div>
</body>
</html>
"""

SAMPLE_BLOCKED_PAGE = """
<!DOCTYPE html>
<html>
<body>
    <h1>Security Check</h1>
    <p>Please verify you are human with recaptcha to continue.</p>
</body>
</html>
"""


def test_browser_discovery_html_parsing():
    config = BrowserDiscoveryConfig(
        source_name="SampleBoard",
        card_selector=".job-card",
        title_selector=".job-title",
        company_selector=".company-name",
        location_selector=".job-location",
        url_selector="a",
        description_selector=".job-description",
    )

    discovery = GenericBrowserDiscovery(config=config)
    postings = discovery.parse_html_cards(SAMPLE_HTML_PAGE, base_url="https://jobs.example.com")

    assert len(postings) == 2

    job1 = postings[0]
    assert job1.title == "Software Developer"
    assert job1.company == "InnoTech Solutions"
    assert job1.remote_type == RemoteType.REMOTE
    assert job1.apply_url == "https://jobs.example.com/jobs/dev-101"
    assert "Python" in job1.skills
    assert "FastAPI" in job1.skills

    job2 = postings[1]
    assert job2.title == "Frontend Intern"
    assert job2.company == "DesignWorks"
    assert job2.location == "San Francisco, CA"


def test_browser_discovery_bot_detection_safeguard():
    config = BrowserDiscoveryConfig(source_name="ProtectedBoard")
    discovery = GenericBrowserDiscovery(config=config)

    # When blocked by captcha / security wall, must not crash or bypass
    postings = discovery.parse_html_cards(SAMPLE_BLOCKED_PAGE, base_url="https://jobs.example.com")
    assert len(postings) == 0
