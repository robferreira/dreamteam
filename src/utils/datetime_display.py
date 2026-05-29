from datetime import UTC, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.settings import get_settings


@lru_cache
def get_display_tz() -> ZoneInfo:
    name = get_settings().display_timezone
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def format_display_datetime(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.astimezone(get_display_tz()).isoformat()


def get_display_timezone_name() -> str:
    return get_settings().display_timezone
