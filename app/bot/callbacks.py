MAX_CALLBACK_DATA_BYTES = 64


def parse_callback_parts(
    data: str | None,
    prefix: str,
    count: int,
) -> tuple[str, ...] | None:
    if not data:
        return None

    if len(data.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
        return None

    prefix_parts = prefix.split(":")
    parts = data.split(":")

    expected_count = len(prefix_parts) + count

    if len(parts) != expected_count:
        return None

    if parts[: len(prefix_parts)] != prefix_parts:
        return None

    values = tuple(parts[len(prefix_parts) :])

    if any(not value for value in values):
        return None

    return values


def parse_positive_int(
    value: str,
) -> int | None:
    try:
        result = int(value)

    except ValueError:
        return None

    if result <= 0:
        return None

    return result


def parse_callback_int(
    data: str | None,
    prefix: str,
) -> int | None:
    parts = parse_callback_parts(
        data=data,
        prefix=prefix,
        count=1,
    )

    if parts is None:
        return None

    return parse_positive_int(parts[0])


def parse_callback_str(
    data: str | None,
    prefix: str,
) -> str | None:
    parts = parse_callback_parts(
        data=data,
        prefix=prefix,
        count=1,
    )

    if parts is None:
        return None

    return parts[0]


def parse_callback_int_str(
    data: str | None,
    prefix: str,
) -> tuple[int, str] | None:
    parts = parse_callback_parts(
        data=data,
        prefix=prefix,
        count=2,
    )

    if parts is None:
        return None

    number = parse_positive_int(parts[0])

    if number is None:
        return None

    return number, parts[1]


class CallbackDataError(ValueError):
    pass


def build_callback_data(
    *parts: str | int,
) -> str:
    values = tuple(str(part) for part in parts)

    if not values:
        raise CallbackDataError("Callback data не содержит частей.")

    if any(not value for value in values):
        raise CallbackDataError("Callback data содержит пустую часть.")

    if any(":" in value for value in values):
        raise CallbackDataError("Часть callback data не должна содержать ':'.")

    data = ":".join(values)

    size = len(data.encode("utf-8"))

    if size > MAX_CALLBACK_DATA_BYTES:
        raise CallbackDataError(
            f"Callback data превышает {MAX_CALLBACK_DATA_BYTES} байт: {size}."
        )

    return data
