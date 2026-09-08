import pytest
from app.models.job import JobPosting
from app.schemas.application_draft import (
    CandidateApplicationContext,
    FieldSource,
    QuestionCategory,
)
from app.services.ai.provider import MockLLMProvider
from app.services.applications.question_answerer import QuestionAnswerer


@pytest.fixture
def candidate_context() -> CandidateApplicationContext:
    return CandidateApplicationContext(
        name="Jordan Lee",
        email="jordan@example.com",
        skills=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
        education=[
            {
                "institution": "University of Engineering",
                "degree": "B.S. in Computer Science",
                "end_date": "2024",
                "gpa": "3.90",
            }
        ],
        projects=[
            {
                "name": "Distributed Task Queue",
                "description": "Built resilient async task workers with Python and Redis.",
            }
        ],
        work_authorization=None,
        sponsorship_required=None,
        expected_salary=None,
        available_from=None,
    )


@pytest.fixture
def job_posting() -> JobPosting:
    return JobPosting(
        id="job_fastapi_01",
        title="Backend Software Engineer",
        company="NexTech",
        description="FastAPI, Python, and async systems",
        skills=["Python", "FastAPI"],
        apply_url="https://nextech.example.com/jobs/1",
        source_hash="sha_nex_1",
    )


@pytest.mark.asyncio
async def test_factual_education_answering(candidate_context, job_posting):
    answerer = QuestionAnswerer(llm_provider=MockLLMProvider())

    q_grad = await answerer.answer_question(
        question_id="q_grad",
        question_text="What is your expected graduation year?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_grad.answer == "2024"
    assert q_grad.source == FieldSource.CANDIDATE_PROFILE
    assert q_grad.confidence == 1.0
    assert q_grad.requires_review is False
    assert q_grad.requires_user_input is False


@pytest.mark.asyncio
async def test_factual_skill_answering(candidate_context, job_posting):
    answerer = QuestionAnswerer(llm_provider=MockLLMProvider())

    q_skill = await answerer.answer_question(
        question_id="q_skill",
        question_text="Do you have experience using Python and FastAPI?",
        context=candidate_context,
        job=job_posting,
    )
    assert "Python" in q_skill.answer
    assert "FastAPI" in q_skill.answer
    assert q_skill.source == FieldSource.CANDIDATE_PROFILE
    assert q_skill.requires_user_input is False


@pytest.mark.asyncio
async def test_sensitive_work_auth_unanswered_flags_user_input(candidate_context, job_posting):
    answerer = QuestionAnswerer(llm_provider=MockLLMProvider())

    # Candidate has no configured work authorization or sponsorship
    q_auth = await answerer.answer_question(
        question_id="q_auth",
        question_text="Are you legally authorized to work in the United States?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_auth.answer is None
    assert q_auth.requires_user_input is True
    assert "user confirmation" in q_auth.warning

    q_sponsor = await answerer.answer_question(
        question_id="q_sponsor",
        question_text="Will you now or in the future require visa sponsorship?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_sponsor.answer is None
    assert q_sponsor.requires_user_input is True


@pytest.mark.asyncio
async def test_sensitive_questions_with_explicit_preferences(candidate_context, job_posting):
    answerer = QuestionAnswerer(llm_provider=MockLLMProvider())

    # Supply explicit candidate preferences
    candidate_context.sponsorship_required = False
    candidate_context.expected_salary = 135000.0
    candidate_context.available_from = "2024-06-01"

    q_sponsor = await answerer.answer_question(
        question_id="q_sponsor",
        question_text="Will you require visa sponsorship?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_sponsor.answer == "No"
    assert q_sponsor.requires_user_input is False
    assert q_sponsor.source == FieldSource.USER_PREFERENCE

    q_sal = await answerer.answer_question(
        question_id="q_sal",
        question_text="What is your desired compensation / expected salary?",
        context=candidate_context,
        job=job_posting,
    )
    assert "$135,000.00" in q_sal.answer
    assert q_sal.requires_user_input is False

    q_avail = await answerer.answer_question(
        question_id="q_avail",
        question_text="When can you start?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_avail.answer == "2024-06-01"
    assert q_avail.requires_user_input is False


@pytest.mark.asyncio
async def test_subjective_motivation_answering_and_review_flag(candidate_context, job_posting):
    answerer = QuestionAnswerer(llm_provider=MockLLMProvider())

    q_why = await answerer.answer_question(
        question_id="q_why",
        question_text="Why do you want to join NexTech as a Backend Software Engineer?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_why.answer is not None
    assert q_why.source in {FieldSource.AI_GENERATED, FieldSource.DERIVED}
    assert q_why.requires_review is True
    assert q_why.requires_user_input is False


@pytest.mark.asyncio
async def test_ai_provider_failure_resilient_fallback(candidate_context, job_posting):
    failing_provider = MockLLMProvider(should_fail=True)
    answerer = QuestionAnswerer(llm_provider=failing_provider)

    q_why = await answerer.answer_question(
        question_id="q_why_fallback",
        question_text="Why are you interested in this position?",
        context=candidate_context,
        job=job_posting,
    )
    assert q_why.answer is not None
    assert "Python" in q_why.answer
    assert q_why.source == FieldSource.DERIVED
    assert "fallback template" in q_why.warning
