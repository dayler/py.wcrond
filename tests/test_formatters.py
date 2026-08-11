import pytest
from datetime import datetime, timezone, timedelta
from wcrond_ctl.formatters import format_datetime

def test_format_datetime_converts_utc_to_local():
    # Setup UTC datetime string
    dt_utc = datetime(2026, 8, 10, 14, 0, 0, tzinfo=timezone.utc)
    iso_str = dt_utc.isoformat()
    
    # Format
    result = format_datetime(iso_str)
    
    # Assert
    # We don't know the exact local timezone of the test runner, but we know it should format correctly
    # without crashing and the result should not have the +00:00 offset anymore.
    assert result != iso_str
    assert "+00:00" not in result
    
    # It should look like "YYYY-MM-DD HH:MM:SS"
    assert len(result) == 19
    assert result.count("-") == 2
    assert result.count(":") == 2

def test_format_datetime_invalid():
    assert format_datetime("Invalid") == "Invalid"
    assert format_datetime("") == ""
    assert format_datetime("Never") == "Never"
    
def test_format_datetime_none():
    assert format_datetime(None) == None
