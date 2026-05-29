from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.tasks.reconciliation import reconcile_orphaned_tasks


@pytest.mark.asyncio
async def test_reconcile_orphaned_tasks():
    with patch(
        "src.tasks.reconciliation.get_task_repository",
    ) as mock_repo_fn:
        mock_repo = AsyncMock()
        mock_repo.reconcile_running_tasks.return_value = 2
        mock_repo_fn.return_value = mock_repo
        count = await reconcile_orphaned_tasks()
    assert count == 2
    mock_repo.reconcile_running_tasks.assert_awaited_once()
