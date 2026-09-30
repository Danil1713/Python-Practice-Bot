def split_telegram_text(
    text: str,
    *,
    max_chars: int = 3500,
) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    if not text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(
            start + max_chars,
            len(text),
        )

        if end < len(text):
            newline_index = text.rfind(
                "\n",
                start,
                end,
            )

            if newline_index > start:
                end = newline_index + 1

        chunk = text[start:end]

        if chunk:
            chunks.append(chunk)

        start = end

    return chunks


def split_telegram_lines(
    lines: list[str],
    *,
    max_chars: int = 3500,
) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    if not lines:
        return []

    chunks: list[str] = []
    current_lines: list[str] = []
    current_length = 0

    for line in lines:
        added_length = len(line)

        if current_lines:
            added_length += 1

        if current_lines and current_length + added_length > max_chars:
            chunks.append("\n".join(current_lines))

            current_lines = []
            current_length = 0

        if len(line) > max_chars:
            if current_lines:
                chunks.append("\n".join(current_lines))

                current_lines = []
                current_length = 0

            line_chunks = split_telegram_text(
                line,
                max_chars=max_chars,
            )

            chunks.extend(line_chunks)
            continue

        current_lines.append(line)

        current_length += added_length

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
