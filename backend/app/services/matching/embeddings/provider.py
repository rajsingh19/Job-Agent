from abc import ABC, abstractmethod
import logging
from typing import List, Optional
import httpx
from app.config.settings import Settings, get_settings
from app.services.exceptions import LLMUnavailableError
from app.services.matching.embeddings.mock import MockEmbeddingGenerator

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding generation."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generates embedding vector for a single text."""
        pass

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for multiple texts."""
        return [await self.embed(t) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API embedding provider using text-embedding-3-small / large."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.base_url = "https://api.openai.com/v1"

    async def embed(self, text: str) -> List[float]:
        if not self.api_key or self.api_key == "mock-key":
            raise LLMUnavailableError("OpenAI API key is missing or not configured.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": text,
            "model": self.model,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                if response.status_code != 200:
                    raise LLMUnavailableError(f"OpenAI embedding error {response.status_code}: {response.text}")

                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            if isinstance(e, LLMUnavailableError):
                raise
            raise LLMUnavailableError(f"OpenAI embedding request failed: {str(e)}")


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic Mock Embedding Provider for tests and offline development."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def embed(self, text: str) -> List[float]:
        if self.should_fail:
            raise LLMUnavailableError("Simulated embedding provider outage.")
        return MockEmbeddingGenerator.generate_vector(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.should_fail:
            raise LLMUnavailableError("Simulated embedding provider outage.")
        return [MockEmbeddingGenerator.generate_vector(t) for t in texts]


def get_embedding_provider(settings: Optional[Settings] = None) -> EmbeddingProvider:
    """Factory helper creating the configured embedding provider."""
    app_settings = settings or get_settings()
    provider_name = app_settings.embedding_provider.lower().strip()

    if provider_name == "openai":
        return OpenAIEmbeddingProvider(
            api_key=app_settings.embedding_api_key,
            model=app_settings.embedding_model,
            timeout_seconds=app_settings.embedding_timeout_seconds,
        )
    elif provider_name == "mock":
        return MockEmbeddingProvider()
    else:
        logger.warning(f"Unknown embedding provider '{provider_name}'. Falling back to MockEmbeddingProvider.")
        return MockEmbeddingProvider()
