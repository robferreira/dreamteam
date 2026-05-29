import hashlib
from functools import lru_cache

from src.settings import get_settings


def _fallback_embedding(text: str, dimension: int) -> list[float]:
    """Embedding determinístico quando sentence-transformers não está disponível."""
    digest = hashlib.sha256(text.encode()).digest()
    values = []
    for i in range(dimension):
        byte_val = digest[i % len(digest)]
        values.append((byte_val / 255.0) * 2 - 1)
    return values


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    dimension = settings.vector_dimension
    try:
        from sentence_transformers import SentenceTransformer

        model = _get_sentence_model(settings.embedding_model)
        vector = model.encode(text, normalize_embeddings=True)
        result = vector.tolist()
        if len(result) != dimension:
            result = result[:dimension] + [0.0] * max(0, dimension - len(result))
        return result
    except ImportError:
        return _fallback_embedding(text, dimension)
    except Exception:
        return _fallback_embedding(text, dimension)


@lru_cache
def _get_sentence_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)
