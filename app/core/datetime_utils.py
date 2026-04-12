from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return a timezone-aware datetime in UTC."""
    return datetime.now(timezone.utc)


def fromtimestamp_utc(timestamp: float) -> datetime:
    """Convert a POSIX timestamp to a timezone-aware UTC datetime."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)
