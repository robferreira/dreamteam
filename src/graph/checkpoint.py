from functools import lru_cache

from src.settings import get_settings

_checkpointer = None


async def get_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        settings = get_settings()
        conn = settings.database_url_sync.replace("postgresql+psycopg", "postgresql")
        _checkpointer = AsyncPostgresSaver.from_conn_string(conn)
        await _checkpointer.setup()
        return _checkpointer
    except Exception:
        return None


@lru_cache
def get_thread_id(task_id: str) -> str:
    return f"task-{task_id}"
