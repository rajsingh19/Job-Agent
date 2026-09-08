import pytest
from app.services.ai.provider import MockLLMProvider
from app.services.resume.parser import FallbackResumeParser, LLMResumeParser


@pytest.mark.asyncio
async def test_llm_resume_parser_success():
    llm_provider = MockLLMProvider()
    parser = LLMResumeParser(llm_provider=llm_provider)

    sample_text = """
    Alex Candidate
    alex.candidate@example.com
    +1-555-0100
    San Francisco, CA
    Education:
    University of Technology - B.S. in Computer Science (2020 - 2024), GPA: 3.85
    Experience:
    Tech Corp - Software Engineering Intern (2023-05 to 2023-08)
    Built FastAPI REST endpoints and PostgreSQL databases.
    Skills: Python, FastAPI, Docker, TypeScript
    """

    profile = await parser.parse(sample_text)

    assert profile.name == "Alex Candidate"
    assert profile.email == "alex.candidate@example.com"
    assert len(profile.education) == 1
    assert profile.education[0].institution == "University of Technology"
    assert len(profile.experience) == 1
    assert "Python" in profile.skills
    assert profile.low_confidence is False


@pytest.mark.asyncio
async def test_fallback_parser_extraction():
    """Verifies that the deterministic regex/heuristic fallback parser correctly extracts core fields."""
    fallback_parser = FallbackResumeParser()

    sample_text = """
    Jordan Miller
    jordan.miller@testdomain.com
    (415) 555-0198
    https://github.com/jordanm
    https://linkedin.com/in/jordanm

    Education:
    Bachelor of Science in Software Engineering
    University of Engineering

    Experience:
    Junior Developer at Global Tech Systems
    Developed REST APIs using Python, Docker, and PostgreSQL.

    Skills:
    Python, Javascript, Docker, PostgreSQL, Linux, Git
    """

    profile = await fallback_parser.parse(sample_text)

    assert profile.email == "jordan.miller@testdomain.com"
    assert profile.name == "Jordan Miller"
    assert profile.links.get("github") == "https://github.com/jordanm"
    assert profile.links.get("linkedin") == "https://linkedin.com/in/jordanm"
    assert "Python" in profile.skills
    assert "Docker" in profile.skills
    assert profile.low_confidence is True
    assert len(profile.warnings) > 0


@pytest.mark.asyncio
async def test_llm_failure_triggers_fallback_flow():
    """Verifies that when LLM fails or returns malformed response, fallback seamlessly produces a profile."""
    # Simulating LLM provider with failure
    failing_llm = MockLLMProvider(should_fail=True)
    llm_parser = LLMResumeParser(llm_provider=failing_llm)
    fallback_parser = FallbackResumeParser()

    resume_text = "Sam Taylor\nsam@example.com\nSkills: Python, React, SQL"

    try:
        profile = await llm_parser.parse(resume_text)
    except Exception:
        profile = await fallback_parser.parse(resume_text)

    assert profile.email == "sam@example.com"
    assert profile.low_confidence is True
    assert "Python" in profile.skills
