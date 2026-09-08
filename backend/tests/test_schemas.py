import pytest
from pydantic import ValidationError
from app.models.enums import RemoteType, ExperienceLevel, ATSProvider
from app.schemas.user import UserCreate
from app.schemas.resume import ResumeProfile, EducationItem, ExperienceItem, ProjectItem
from app.schemas.preferences import UserPreferencesCreate
from app.schemas.job import JobPostingCreate
from app.schemas.application import ReviewPackage, GeneratedAnswer


def test_user_schema_email_validation():
    user = UserCreate(email="valid.email@example.com")
    assert user.email == "valid.email@example.com"

    with pytest.raises(ValidationError):
        UserCreate(email="not-a-valid-email")


def test_resume_profile_schema():
    profile = ResumeProfile(
        name="Alex Smith",
        email="alex@example.com",
        phone="+1-555-0199",
        location="New York, NY",
        education=[
            EducationItem(
                institution="Columbia University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date="2020",
                end_date="2024",
                gpa="3.9",
            )
        ],
        experience=[
            ExperienceItem(
                company="Acme Corp",
                role="Software Engineering Intern",
                location="Remote",
                start_date="2023-05",
                end_date="2023-08",
                is_current=False,
                description="Built REST APIs using FastAPI.",
                skills_used=["Python", "FastAPI", "Docker"],
            )
        ],
        projects=[
            ProjectItem(
                name="AI Job Search Agent",
                role="Lead Developer",
                description="Autonomous job discovery agent",
                tech_stack=["Python", "Playwright", "FastAPI"],
            )
        ],
        skills=["Python", "TypeScript", "SQL", "Playwright"],
        links={"github": "https://github.com/alexsmith", "linkedin": "https://linkedin.com/in/alexsmith"},
    )

    assert profile.name == "Alex Smith"
    assert len(profile.education) == 1
    assert profile.education[0].institution == "Columbia University"
    assert len(profile.experience) == 1
    assert len(profile.projects) == 1
    assert len(profile.skills) == 4


def test_user_preferences_schema_separation():
    """Ensure user preferences are strongly typed and separated from resume data."""
    prefs = UserPreferencesCreate(
        user_id="user-123",
        target_roles=["Backend Engineer", "Software Engineer"],
        preferred_locations=["San Francisco", "Remote"],
        remote_preference=RemoteType.REMOTE,
        minimum_stipend=80000.0,
        experience_level=ExperienceLevel.MID_LEVEL,
        required_skills=["Python", "PostgreSQL"],
        excluded_companies=["SpammyCorp"],
    )

    assert prefs.user_id == "user-123"
    assert prefs.remote_preference == RemoteType.REMOTE
    assert prefs.minimum_stipend == 80000.0
    assert "SpammyCorp" in prefs.excluded_companies


def test_job_posting_schema():
    job = JobPostingCreate(
        source="ASHBY",
        title="Full Stack Engineer",
        company="FutureAI",
        location="San Francisco, CA",
        remote_type=RemoteType.HYBRID,
        description="Join our engineering team building AI tools.",
        skills=["Python", "React", "Next.js"],
        stipend_min=120000.0,
        stipend_max=160000.0,
        apply_url="https://jobs.ashbyhq.com/futureai/123",
        ats_provider=ATSProvider.ASHBY,
        source_hash="sha256_ashby_123",
    )

    assert job.source == "ASHBY"
    assert job.ats_provider == ATSProvider.ASHBY
    assert job.source_hash == "sha256_ashby_123"


def test_review_package_schema():
    package = ReviewPackage(
        job_title="Backend Developer",
        company="Tech Innovators",
        apply_url="https://jobs.lever.co/techinnovators/123",
        selected_resume_id="resume-uuid-456",
        populated_fields={"name": "Alex Smith", "email": "alex@example.com"},
        generated_answers=[
            GeneratedAnswer(
                question_id="q1",
                question_text="Why are you interested in this role?",
                answer_text="I have strong experience in Python and distributed systems.",
                confidence_score=0.95,
                grounded_in_field="experience[0]",
            )
        ],
        warnings=["Salary expectation was not provided in candidate preferences."],
    )

    assert package.job_title == "Backend Developer"
    assert len(package.generated_answers) == 1
    assert len(package.warnings) == 1
