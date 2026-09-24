from app.bot.callbacks import (
    MAX_CALLBACK_DATA_BYTES,
    CallbackDataError,
    build_callback_data,
    parse_callback_int,
    parse_callback_int_str,
    parse_callback_parts,
    parse_callback_str,
)


def test_parse_callback_int():
    assert (
        parse_callback_int(
            "project:hints:15",
            "project:hints",
        )
        == 15
    )


def test_parse_callback_str():
    assert (
        parse_callback_str(
            "admin:menu:python_start",
            "admin:menu",
        )
        == "python_start"
    )


def test_parse_callback_int_str():
    assert (
        parse_callback_int_str(
            "admin:post:12:python_start",
            "admin:post",
        )
        == (
            12,
            "python_start",
        )
    )


def test_invalid_integer_callbacks():
    invalid_values = [
        None,
        "",
        "project:hints",
        "project:hints:",
        "project:hints:abc",
        "project:hints:-1",
        "project:hints:0",
        "project:hints:1:2",
        "wrong:15",
    ]

    for value in invalid_values:
        assert (
            parse_callback_int(
                value,
                "project:hints",
            )
            is None
        )


def test_wrong_number_of_parts_is_rejected():
    assert (
        parse_callback_parts(
            "admin:post:12",
            "admin:post",
            count=2,
        )
        is None
    )

    assert (
        parse_callback_parts(
            "admin:post:12:course:extra",
            "admin:post",
            count=2,
        )
        is None
    )


def test_callback_over_64_bytes_is_rejected():
    long_value = (
        "x" * (
            MAX_CALLBACK_DATA_BYTES + 1
        )
    )

    assert (
        parse_callback_str(
            f"test:{long_value}",
            "test",
        )
        is None
    )

def test_build_callback_data():
    assert (
        build_callback_data(
            "project",
            "open",
            15,
        )
        == "project:open:15"
    )


def test_build_callback_data_allows_64_bytes():
    value = "a" * 62

    result = build_callback_data(
        "x",
        value,
    )

    assert (
        len(result.encode("utf-8"))
        == 64
    )


def test_build_callback_data_rejects_over_64_bytes():
    value = "a" * 63

    try:
        build_callback_data(
            "x",
            value,
        )

    except CallbackDataError:
        pass

    else:
        raise AssertionError(
            "Callback длиннее 64 байт "
            "должен быть отклонён."
        )


def test_build_callback_data_counts_utf8_bytes():
    value = "я" * 32

    try:
        build_callback_data(
            "x",
            value,
        )

    except CallbackDataError:
        pass

    else:
        raise AssertionError(
            "Нужно считать UTF-8 байты, "
            "а не количество символов."
        )


def test_build_callback_data_rejects_colon_inside_part():
    try:
        build_callback_data(
            "course",
            "bad:slug",
        )

    except CallbackDataError:
        pass

    else:
        raise AssertionError(
            "':' внутри части должен "
            "быть запрещён."
        )