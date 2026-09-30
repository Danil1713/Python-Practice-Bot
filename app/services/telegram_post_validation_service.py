from html.parser import HTMLParser

TELEGRAM_MESSAGE_TEXT_LIMIT = 4096

_ALLOWED_TAGS = {
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ins",
    "s",
    "strike",
    "del",
    "span",
    "tg-spoiler",
    "a",
    "tg-emoji",
    "code",
    "pre",
    "blockquote",
}


class TelegramPostValidationError(ValueError):
    pass


class _TelegramHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)

        self.stack: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.lower()

        if tag not in _ALLOWED_TAGS:
            raise TelegramPostValidationError(
                f"HTML-тег <{tag}> не поддерживается Telegram."
            )

        self._validate_attributes(
            tag,
            attrs,
        )

        self.stack.append(tag)

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        tag = tag.lower()

        if not self.stack or self.stack[-1] != tag:
            raise TelegramPostValidationError(
                f"Некорректная HTML-разметка: неожиданный </{tag}>."
            )

        self.stack.pop()

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        raise TelegramPostValidationError(
            "Самозакрывающиеся HTML-теги не поддерживаются."
        )

    def handle_data(
        self,
        data: str,
    ) -> None:
        self.text_parts.append(data)

    def _validate_attributes(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = {name.lower(): value for name, value in attrs}

        if tag == "a":
            if set(attributes) != {"href"} or not attributes["href"]:
                raise TelegramPostValidationError(
                    "Тег <a> должен содержать только атрибут href."
                )

            return

        if tag == "span":
            if attributes != {"class": "tg-spoiler"}:
                raise TelegramPostValidationError(
                    'Для <span> поддерживается только class="tg-spoiler".'
                )

            return

        if tag == "tg-emoji":
            if set(attributes) != {"emoji-id"} or not attributes["emoji-id"]:
                raise TelegramPostValidationError(
                    "<tg-emoji> должен содержать атрибут emoji-id."
                )

            return

        if tag == "blockquote":
            if not attributes:
                return

            if attributes == {"expandable": None}:
                return

            raise TelegramPostValidationError(
                "Некорректные атрибуты тега <blockquote>."
            )

        if tag == "code":
            if not attributes:
                return

            class_value = attributes.get("class")

            if (
                set(attributes) == {"class"}
                and class_value is not None
                and class_value.startswith("language-")
            ):
                return

            raise TelegramPostValidationError("Некорректные атрибуты тега <code>.")

        if attributes:
            raise TelegramPostValidationError(
                f"Тег <{tag}> не должен содержать атрибуты."
            )

    def get_visible_text(
        self,
    ) -> str:
        return "".join(self.text_parts)


def get_telegram_post_visible_text(
    content: str,
) -> str:
    parser = _TelegramHTMLParser()

    try:
        parser.feed(content)
        parser.close()

    except TelegramPostValidationError:
        raise

    except Exception as error:
        raise TelegramPostValidationError(
            "Не удалось разобрать HTML-разметку публикации."
        ) from error

    if parser.stack:
        tag = parser.stack[-1]

        raise TelegramPostValidationError(
            f"Некорректная HTML-разметка: тег <{tag}> не закрыт."
        )

    return parser.get_visible_text()


def validate_telegram_post_content(
    content: str,
) -> None:
    visible_text = get_telegram_post_visible_text(content)

    if not visible_text.strip():
        raise TelegramPostValidationError("Текст публикации пустой.")

    visible_length = len(visible_text)

    if visible_length > TELEGRAM_MESSAGE_TEXT_LIMIT:
        raise TelegramPostValidationError(
            "Текст публикации слишком "
            "длинный: "
            f"{visible_length} символов. "
            "Максимум — "
            f"{TELEGRAM_MESSAGE_TEXT_LIMIT}."
        )


def build_telegram_post_preview(
    content: str,
    *,
    max_chars: int = 2000,
) -> str:
    visible_text = get_telegram_post_visible_text(content)

    if len(visible_text) <= max_chars:
        return visible_text

    return visible_text[: max_chars - 1] + "…"
