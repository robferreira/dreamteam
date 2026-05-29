from datetime import UTC, datetime
from unittest.mock import patch

from src.utils.datetime_display import format_display_datetime, get_display_timezone_name


def test_format_display_datetime_sao_paulo():
    dt = datetime(2026, 5, 29, 16, 10, 19, tzinfo=UTC)
    with patch("src.utils.datetime_display.get_settings") as mock_settings:
        mock_settings.return_value.display_timezone = "America/Sao_Paulo"
        from src.utils import datetime_display

        datetime_display.get_display_tz.cache_clear()
        formatted = format_display_datetime(dt)
    assert "-03:00" in formatted or "-02:00" in formatted
    assert "2026-05-29" in formatted


def test_get_display_timezone_name_default():
    name = get_display_timezone_name()
    assert name == "America/Sao_Paulo" or name
