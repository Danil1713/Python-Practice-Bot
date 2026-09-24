from datetime import UTC, datetime
from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
)


DATETIME_FORMAT = "%d.%m.%Y %H:%M"


class InvalidDateTimeFormat(ValueError):
    pass


class NonexistentLocalTime(ValueError):
    pass


class AmbiguousLocalTime(ValueError):
    pass


def parse_local_datetime_to_utc(
    value: str,
    timezone_name: str,
) -> datetime:
    try:
        naive = datetime.strptime(
            value,
            DATETIME_FORMAT,
        )

    except ValueError as error:
        raise InvalidDateTimeFormat from error

    try:
        timezone = ZoneInfo(
            timezone_name
        )

    except ZoneInfoNotFoundError as error:
        raise RuntimeError(
            "Неизвестный часовой пояс: "
            f"{timezone_name}"
        ) from error

    valid_datetimes: list[datetime] = []

    for fold in (0, 1):
        local_datetime = naive.replace(
            tzinfo=timezone,
            fold=fold,
        )

        roundtrip = (
            local_datetime
            .astimezone(UTC)
            .astimezone(timezone)
        )

        if (
            roundtrip.replace(tzinfo=None)
            == naive
            and roundtrip.fold == fold
        ):
            valid_datetimes.append(
                local_datetime
            )

    if not valid_datetimes:
        raise NonexistentLocalTime

    if len(valid_datetimes) > 1:
        raise AmbiguousLocalTime

    return valid_datetimes[0].astimezone(
        UTC
    )