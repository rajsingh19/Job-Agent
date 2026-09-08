from abc import ABC, abstractmethod
import json
import logging
from typing import Any, Dict, Optional
import httpx
from app.config.settings import Settings, get_settings
from app.services.exceptions import LLMUnavailableError, LLMParseFailedError

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract interface for LLM provider."""

    @abstractmethod
    async def generate_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        """Generate structured JSON response from the LLM."""
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: str) -> str:
        """Generate free-form text response from the LLM."""
        pass


class OpenAILLMProvider(LLMProvider):
    """OpenAI API provider for structured JSON and text generation."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", temperature: float = 0.2):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = "https://api.openai.com/v1"

    async def generate_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "mock-key":
            raise LLMUnavailableError("OpenAI API key is missing or not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code != 200:
                    logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                    raise LLMUnavailableError(f"OpenAI service returned error status {response.status_code}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(f"OpenAI network/timeout error: {e}")
            raise LLMUnavailableError(f"OpenAI request timed out or network error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode OpenAI JSON response: {e}")
            raise LLMParseFailedError(f"Model returned invalid JSON: {str(e)}")
        except Exception as e:
            if isinstance(e, (LLMUnavailableError, LLMParseFailedError)):
                raise
            raise LLMUnavailableError(f"OpenAI client error: {str(e)}")

    async def generate_text(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key or self.api_key == "mock-key":
            raise LLMUnavailableError("OpenAI API key is missing or not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code != 200:
                    logger.error(f"OpenAI API error {response.status_code}: {response.text}")
                    raise LLMUnavailableError(f"OpenAI service returned error status {response.status_code}")

                data = response.json()
                return data["choices"][0]["message"]["content"]
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.error(f"OpenAI network/timeout error: {e}")
            raise LLMUnavailableError(f"OpenAI request timed out or network error: {str(e)}")
        except Exception as e:
            if isinstance(e, LLMUnavailableError):
                raise
            raise LLMUnavailableError(f"OpenAI client error: {str(e)}")


class GroqLLMProvider(LLMProvider):
    """Groq API provider for fast open-weight model JSON inference."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.2):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = "https://api.groq.com/openai/v1"

    async def generate_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "mock-key":
            raise LLMUnavailableError("Groq API key is missing or not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code != 200:
                    raise LLMUnavailableError(f"Groq returned error status {response.status_code}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            if isinstance(e, (LLMUnavailableError, LLMParseFailedError)):
                raise
            raise LLMUnavailableError(f"Groq request failed: {str(e)}")

    async def generate_text(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key or self.api_key == "mock-key":
            raise LLMUnavailableError("Groq API key is missing or not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code != 200:
                    raise LLMUnavailableError(f"Groq returned error status {response.status_code}")

                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            if isinstance(e, LLMUnavailableError):
                raise
            raise LLMUnavailableError(f"Groq request failed: {str(e)}")


class OllamaLLMProvider(LLMProvider):
    """Ollama local self-hosted LLM provider."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model

    async def generate_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                if response.status_code != 200:
                    raise LLMUnavailableError(f"Ollama returned status {response.status_code}")
                data = response.json()
                content = data["message"]["content"]
                return json.loads(content)
        except Exception as e:
            raise LLMUnavailableError(f"Ollama request failed: {str(e)}")

    async def generate_text(self, prompt: str, system_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                if response.status_code != 200:
                    raise LLMUnavailableError(f"Ollama returned status {response.status_code}")
                data = response.json()
                return data["message"]["content"]
        except Exception as e:
            raise LLMUnavailableError(f"Ollama request failed: {str(e)}")


class MockLLMProvider(LLMProvider):
    """
    Deterministic Mock LLM Provider for unit testing and local development without API keys.
    Extracts structured fields deterministically from standard resume patterns.
    """

    def __init__(self, should_fail: bool = False, malformed_json: bool = False):
        self.should_fail = should_fail
        self.malformed_json = malformed_json

    async def generate_text(self, prompt: str, system_prompt: str) -> str:
        if self.should_fail:
            raise LLMUnavailableError("Mock LLM simulated provider failure.")

        prompt_lower = prompt.lower()
        if "cover letter" in prompt_lower or "cover letter" in system_prompt.lower():
            return (
                "Dear Hiring Team,\n\n"
                "I am writing to express my strong enthusiasm for this engineering opportunity. "
                "With hands-on experience building backend systems using Python, FastAPI, and PostgreSQL, "
                "I have developed high-performance services and automated complex workflows. "
                "I would love to bring these technical capabilities and dedication to your team.\n\n"
                "Sincerely,\nCandidate"
            )
        elif "why are you interested" in prompt_lower or "motivation" in prompt_lower:
            return "I am excited by the company's mission and the opportunity to apply my Python and backend expertise to high-impact challenges."
        elif "project" in prompt_lower:
            return "I architected an autonomous job application agent with Python and FastAPI, improving workflow efficiency."
        return "I bring extensive experience in software development, collaborative problem solving, and building resilient systems."

    async def generate_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        if self.should_fail:
            raise LLMUnavailableError("Mock LLM simulated provider failure.")

        if self.malformed_json:
            raise LLMParseFailedError("Mock LLM returned malformed JSON.")

        # Return structured resume profile extracted from prompt text
        # If text contains specific keywords, reflect them
        import re

        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt)
        email = email_match.group(0) if email_match else "mock.candidate@example.com"

        phone_match = re.search(r"(\+?\d[\d -]{8,}\d)", prompt)
        phone = phone_match.group(0) if phone_match else "+1-555-0100"

        return {
            "name": "Alex Candidate",
            "email": email,
            "phone": phone,
            "location": "San Francisco, CA",
            "summary": "Passionate software engineer experienced in Python and modern web architectures.",
            "education": [
                {
                    "institution": "University of Technology",
                    "degree": "B.S. in Computer Science",
                    "field_of_study": "Computer Science",
                    "start_date": "2020",
                    "end_date": "2024",
                    "gpa": "3.85",
                    "highlights": ["Dean's Honor List", "President of Coding Club"],
                }
            ],
            "experience": [
                {
                    "company": "Tech Corp",
                    "role": "Software Engineering Intern",
                    "location": "San Francisco, CA",
                    "start_date": "2023-05",
                    "end_date": "2023-08",
                    "is_current": False,
                    "description": "Developed high-performance REST APIs with FastAPI and PostgreSQL.",
                    "highlights": ["Reduced API latency by 40%"],
                    "skills_used": ["Python", "FastAPI", "PostgreSQL", "Docker"],
                }
            ],
            "projects": [
                {
                    "name": "Job Application Agent",
                    "role": "Lead Architect",
                    "description": "Autonomous job search and application preparation platform.",
                    "url": "https://github.com/alex/job-agent",
                    "tech_stack": ["Python", "FastAPI", "Playwright", "Next.js"],
                    "highlights": ["Automated ATS form filling"],
                }
            ],
            "skills": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker", "TypeScript", "React"],
            "certifications": [
                {
                    "name": "AWS Certified Developer",
                    "issuer": "Amazon Web Services",
                    "issue_date": "2023-09",
                    "expiry_date": "2026-09",
                    "credential_id": "AWS-123456",
                    "url": "https://aws.amazon.com/verify/AWS-123456",
                }
            ],
            "achievements": ["1st Place Hackathon Winner 2023"],
            "languages": ["English (Native)", "Spanish (Conversational)"],
            "links": {
                "github": "https://github.com/alexcandidate",
                "linkedin": "https://linkedin.com/in/alexcandidate",
            },
        }


def get_llm_provider(settings: Optional[Settings] = None) -> LLMProvider:
    """Factory helper creating the configured LLM provider."""
    if settings is None:
        settings = get_settings()

    provider_name = settings.llm_provider.lower().strip()

    if provider_name == "openai":
        return OpenAILLMProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
    elif provider_name == "groq":
        return GroqLLMProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )
    elif provider_name == "ollama":
        return OllamaLLMProvider(model=settings.llm_model)
    elif provider_name == "mock":
        return MockLLMProvider()
    else:
        logger.warning(f"Unknown LLM provider '{provider_name}'. Falling back to MockLLMProvider.")
        return MockLLMProvider()
