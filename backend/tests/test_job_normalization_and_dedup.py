import pytest
from app.models.enums import ATSProvider, ExperienceLevel, JobSourceType, RemoteType
from app.schemas.job import JobPostingCreate
from app.services.discovery.deduplication import JobDeduplicator
from app.services.discovery.normalization import JobNormalizer


def test_normalize_company_name():
    assert JobNormalizer.normalize_company_name("Acme Corp, Inc.") == "Acme"
    assert JobNormalizer.normalize_company_name("Tech Solutions LLC") == "Tech Solutions"
    assert JobNormalizer.normalize_company_name("Global Systems Pvt Ltd.") == "Global Systems"
    assert JobNormalizer.normalize_company_name("Stripe") == "Stripe"


def test_normalize_job_title():
    assert JobNormalizer.normalize_title("Sr. SWE") == "Senior Software Engineer"
    assert JobNormalizer.normalize_title("Jr. Dev - Python") == "Junior Developer - Python"
    assert JobNormalizer.normalize_title("AI/ML Engineer 🚀") == "AI / Machine Learning Engineer"
    assert JobNormalizer.normalize_title("Lead SDE (Backend)") == "Lead Software Development Engineer Backend"


def test_normalize_location_and_remote():
    assert JobNormalizer.normalize_location("San Francisco, CA, USA") == "San Francisco, CA, USA"
    assert JobNormalizer.normalize_location("Anywhere - Remote") == "Remote"

    assert JobNormalizer.detect_remote_type("Software Engineer", "Remote", "") == RemoteType.REMOTE
    assert JobNormalizer.detect_remote_type("Backend Dev", "New York, NY", "This is a hybrid role (3 days in office).") == RemoteType.HYBRID
    assert JobNormalizer.detect_remote_type("Systems Eng", "Austin, TX", "100% on-site in Austin.") == RemoteType.ON_SITE


def test_detect_experience_level():
    assert JobNormalizer.detect_experience_level("Software Engineering Intern", "") == ExperienceLevel.INTERNSHIP
    assert JobNormalizer.detect_experience_level("Junior Frontend Developer", "") == ExperienceLevel.ENTRY_LEVEL
    assert JobNormalizer.detect_experience_level("Senior Backend Engineer", "") == ExperienceLevel.SENIOR_LEVEL
    assert JobNormalizer.detect_experience_level("Staff Infrastructure Architect", "") == ExperienceLevel.LEAD


def test_clean_html_description_and_skills():
    html_desc = "<p>Join our team!</p><ul><li>Proficiency in <strong>Python</strong> and <strong>FastAPI</strong></li><li>Experience with <strong>Docker</strong></li></ul>"
    clean_text = JobNormalizer.clean_html_description(html_desc)

    assert "Join our team!" in clean_text
    assert "<p>" not in clean_text
    assert "<strong>" not in clean_text

    skills = JobNormalizer.extract_skills("Backend Developer", clean_text)
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills


def test_deduplication_exact_and_fuzzy():
    job1 = JobPostingCreate(
        source="GREENHOUSE",
        source_type=JobSourceType.API,
        external_id="12345",
        title="Senior Software Engineer",
        company="Stripe",
        location="San Francisco, CA",
        remote_type=RemoteType.REMOTE,
        description="Python backend position",
        skills=["Python"],
        apply_url="https://boards.greenhouse.io/stripe/jobs/12345",
        source_hash=JobDeduplicator.generate_source_hash("GREENHOUSE", "12345", "Stripe", "Senior Software Engineer", "San Francisco, CA", "https://boards.greenhouse.io/stripe/jobs/12345"),
    )

    # Identical job from a different aggregator (e.g. slight title formatting differences)
    job2 = JobPostingCreate(
        source="GENERIC_BROWSER",
        source_type=JobSourceType.BROWSER,
        external_id=None,
        title="Senior Software Engineer",
        company="Stripe",
        location="San Francisco, CA",
        remote_type=RemoteType.REMOTE,
        description="Python backend role",
        skills=["Python"],
        apply_url="https://stripe.com/jobs/12345",
        source_hash=JobDeduplicator.generate_source_hash("GENERIC_BROWSER", None, "Stripe", "Senior Software Engineer", "San Francisco, CA", "https://stripe.com/jobs/12345"),
    )

    # Distinct job (different company)
    job3 = JobPostingCreate(
        source="LEVER",
        source_type=JobSourceType.API,
        external_id="99999",
        title="Senior Software Engineer",
        company="Palantir",
        location="San Francisco, CA",
        remote_type=RemoteType.REMOTE,
        description="Python engineering position",
        skills=["Python"],
        apply_url="https://jobs.lever.co/palantir/99999",
        source_hash=JobDeduplicator.generate_source_hash("LEVER", "99999", "Palantir", "Senior Software Engineer", "San Francisco, CA", "https://jobs.lever.co/palantir/99999"),
    )

    # Distinct job (different role at same company)
    job4 = JobPostingCreate(
        source="GREENHOUSE",
        source_type=JobSourceType.API,
        external_id="12346",
        title="Product Manager",
        company="Stripe",
        location="San Francisco, CA",
        remote_type=RemoteType.REMOTE,
        description="Product management position",
        skills=[],
        apply_url="https://boards.greenhouse.io/stripe/jobs/12346",
        source_hash=JobDeduplicator.generate_source_hash("GREENHOUSE", "12346", "Stripe", "Product Manager", "San Francisco, CA", "https://boards.greenhouse.io/stripe/jobs/12346"),
    )

    all_jobs = [job1, job2, job3, job4]
    unique_jobs, dups_removed = JobDeduplicator.deduplicate_postings(all_jobs)

    assert dups_removed == 1
    assert len(unique_jobs) == 3
    companies = [j.company for j in unique_jobs]
    assert "Stripe" in companies
    assert "Palantir" in companies
