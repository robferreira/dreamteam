from src.logging_config import get_logger
from src.memory.postgres import get_task_repository

logger = get_logger(__name__)

INTERRUPTED_MESSAGE = "Execução interrompida: serviço reiniciado ou worker inativo"


async def reconcile_orphaned_tasks() -> int:
    repo = get_task_repository()
    count = await repo.reconcile_running_tasks(error=INTERRUPTED_MESSAGE)
    if count:
        logger.info("orphaned_tasks_reconciled", count=count)
    return count
