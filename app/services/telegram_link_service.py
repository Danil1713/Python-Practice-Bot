def build_channel_message_url(
    channel_id: int,
    message_id: int,
) -> str | None:
    raw_channel_id = str(channel_id)

    if not raw_channel_id.startswith("-100"):
        return None

    internal_channel_id = raw_channel_id[4:]

    if (
        not internal_channel_id.isdigit()
        or message_id <= 0
    ):
        return None

    return (
        "https://t.me/c/"
        f"{internal_channel_id}/"
        f"{message_id}"
    )