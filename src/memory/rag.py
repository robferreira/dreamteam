from functools import lru_cache
from typing import Any

from src.config import MEMORY_DIR
from src.memory.postgres import get_memory_document_repository
from src.memory.vector import embed_text
from src.settings import get_settings


@lru_cache
def _get_repo():
    return get_memory_document_repository()


async def retrieve_context(
    query: str,
    project_id: str = "default",
    doc_types: list[str] | None = None,
    limit: int = 5,
) -> str:
    settings = get_settings()
    try:
        embedding = await embed_text(query)
        repo = _get_repo()
        docs = await repo.search_similar(
            embedding=embedding,
            project_id=project_id,
            limit=limit,
            doc_types=doc_types,
        )
        if not docs:
            return ""
        parts = []
        for doc in docs:
            parts.append(f"[{doc.doc_type}]\n{doc.content[:2000]}")
        return "\n\n---\n\n".join(parts)
    except Exception:
        return ""


async def index_document(
    project_id: str,
    doc_type: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    embedding = await embed_text(content)
    repo = _get_repo()
    await repo.add_document(
        project_id=project_id,
        doc_type=doc_type,
        content=content,
        embedding=embedding,
        metadata=metadata,
    )


async def bootstrap_standards(project_id: str = "default") -> None:
    """Indexa memory/standards.md para RAG de specialists."""
    standards_path = MEMORY_DIR / "standards.md"
    if not standards_path.exists():
        return
    try:
        content = standards_path.read_text(encoding="utf-8")
        repo = _get_repo()
        existing = await repo.search_similar(
            embedding=await embed_text("code standards"),
            project_id=project_id,
            limit=1,
            doc_types=["standards"],
        )
        if existing:
            return
        await index_document(
            project_id=project_id,
            doc_type="standards",
            content=content,
            metadata={"source": str(standards_path.name)},
        )
    except Exception:
        return
