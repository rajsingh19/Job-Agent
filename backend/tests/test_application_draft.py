import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enums import JobSourceType, RemoteType
from app.models.job import JobPosting
from app.models.profile import UserPreference
from app.models.resume import Resume
from app.services.applications.draft_service import ApplicationDraftService


@pytest_asyncio.fixture
async def seed_draft_entities(db_session: AsyncSession):
    # Candidate Preferences
    pref = UserPreference(
        user_id="user_draft_01",
        target_roles=["Senior Python Engineer"],
        preferred_locations=["Remote"],
        remote_preference=RemoteType.REMOTE.value,
        minimum_stipend=120000.0,
        additional_preferences={
            "work_authorization": "US Citizen",
            "sponsorship_required": False,
            "expected_salary": 140000.0,
            "available_from": "2024-07-01",
        },
    )
    db_session.add(pref)

    # Resume
    resume = Resume(
        id="res_draft_01",
        user_id="user_draft_01",
        name="jordan_resume.pdf",
        file_reference="user_draft_01/resumes/jordan.pdf",
        content_hash="hash_jordan_draft",
        is_default=True,
        parsed_profile={
            "name": "Jordan Dev",
            "email": "jordan.dev@example.com",
            "phone": "+1-555-0199",
            "location": "San Francisco, CA",
            "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS"],
            "experience": [
                {
                    "company": "CloudCorp",
                    "role": "Backend Engineer",
                    "description": "Developed async microservices with FastAPI and PostgreSQL.",
                }
            ],
            "education": [
                {
                    "institution": "State University",
                    "degree": "B.S. in Computer Science",
                    "end_date": "2024",
                }
            ],
            "projects": [
                {
                    "name": "Job Agent Platform",
                    "description": "Autonomous application drafting and ATS routing.",
                }
            ],
            "links": {
                "linkedin": "https://linkedin.com/in/jordandev",
                "github": "https://github.com/jordandev",
            },
        },
    )
    db_session.add(resume)

    # Job Posting
    job = JobPosting(
        id="job_draft_gh_01",
        source="GREENHOUSE",
        source_type=JobSourceType.API.value,
        external_id="gh_draft_01",
        title="Senior Python Backend Developer",
        company="Stripe",
        location="Remote",
        remote_type=RemoteType.REMOTE.value,
        description="Seeking Senior Python Backend Developer with FastAPI and microservices experience.",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        apply_url="https://boards.greenhouse.io/stripe/jobs/draft01",
        source_hash="sha_draft_gh_01",
        is_active=True,
    )
    db_session.add(job)

    await db_session.commit()


@pytest.mark.asyncio
async def test_application_draft_creation_and_retrieval(db_session: AsyncSession, seed_draft_entities):
    service = ApplicationDraftService()

    custom_questions = [
        {"question_id": "q_auth", "question": "Are you authorized to work in the US?"},
        {"question_id": "q_sponsor", "question": "Will you require visa sponsorship?"},
        {"question_id": "q_why", "question": "Why are you interested in joining Stripe?"},
    ]

    draft = await service.create_draft(
        db=db_session,
        user_id="user_draft_01",
        job_id="job_draft_gh_01",
        custom_questions=custom_questions,
        include_cover_letter=True,
    )

    # Verify Draft Core Fields
    assert draft.user_id == "user_draft_01"
    assert draft.job_id == "job_draft_gh_01"
    assert draft.resume_id == "res_draft_01"
    assert draft.platform == "greenhouse"
    assert draft.application_method == "ats"

    # Verify Standard Form Fields
    field_map = {f.field_id: f.value for f in draft.fields}
    assert field_map["full_name"] == "Jordan Dev"
    assert field_map["email"] == "jordan.dev@example.com"
    assert field_map["phone"] == "+1-555-0199"
    assert field_map["linkedin_url"] == "https://linkedin.com/in/jordandev"

    # Verify Custom Questions
    q_map = {q.question_id: q for q in draft.custom_questions}
    assert q_map["q_auth"].answer == "US Citizen"
    assert q_map["q_auth"].requires_user_input is False

    assert q_map["q_sponsor"].answer == "No"
    assert q_map["q_sponsor"].requires_user_input is False

    assert q_map["q_why"].answer is not None
    assert q_map["q_why"].requires_review is True

    # Verify Cover Letter
    assert draft.cover_letter is not None
    assert "Jordan Dev" in draft.cover_letter or "Candidate" in draft.cover_letter

    # Verify Draft Status in DB
    retrieved = await service.get_draft(
        db=db_session,
        user_id="user_draft_01",
        application_id=draft.id,
    )
    assert retrieved.id == draft.id
    assert retrieved.ready_for_review is True
    assert retrieved.requires_user_input is False
