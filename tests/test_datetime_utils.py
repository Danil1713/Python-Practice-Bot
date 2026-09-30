import pytest

from app.utils.datetime_utils import (
    AmbiguousLocalTime,
    NonexistentLocalTime,
    parse_local_datetime_to_utc,
)


def test_normal_local_datetime():
    result = parse_local_datetime_to_utc(
        "23.09.2026 18:30",
        "Europe/Vienna",
    )

    assert result.isoformat() == ("2026-09-23T16:30:00+00:00")


def test_nonexistent_dst_datetime():
    with pytest.raises(NonexistentLocalTime):
        parse_local_datetime_to_utc(
            "29.03.2026 02:30",
            "Europe/Vienna",
        )


def test_ambiguous_dst_datetime():
    with pytest.raises(AmbiguousLocalTime):
        parse_local_datetime_to_utc(
            "25.10.2026 02:30",
            "Europe/Vienna",
        )
