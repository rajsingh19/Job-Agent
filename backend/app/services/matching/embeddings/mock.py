import hashlib
import math
import re
from typing import List


class MockEmbeddingGenerator:
    """
    Generates deterministic 128-dimensional unit embeddings from text tokens and n-grams.
    Ensures that identical text yields identical vectors and semantically overlapping texts
    yield high cosine similarity, while unrelated texts yield low similarity.
    """

    DIMENSIONS = 128

    @classmethod
    def generate_vector(cls, text: str) -> List[float]:
        if not text or not text.strip():
            # Return a zero vector
            return [0.0] * cls.DIMENSIONS

        tokens = re.findall(r"\w+", text.lower())
        vector = [0.0] * cls.DIMENSIONS

        for token in tokens:
            # Deterministic hash to bucket
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            index = h % cls.DIMENSIONS
            sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
            vector[index] += sign * (1.0 + len(token) * 0.1)

        # Normalize to unit length (L2 norm)
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            return [v / magnitude for v in vector]
        return [0.0] * cls.DIMENSIONS

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two unit vectors (range -1.0 to 1.0)."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        similarity = dot_product / (mag_a * mag_b)
        # Clamp to [-1.0, 1.0] to guard against floating point inaccuracies
        return max(-1.0, min(1.0, similarity))
