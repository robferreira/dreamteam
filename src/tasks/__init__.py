__all__ = ["TaskService", "get_task_service"]


def __getattr__(name: str):
    if name in ("TaskService", "get_task_service"):
        from src.tasks.service import TaskService, get_task_service

        return TaskService if name == "TaskService" else get_task_service
    raise AttributeError(name)
