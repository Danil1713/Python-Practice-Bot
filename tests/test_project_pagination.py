from types import SimpleNamespace

from app.bot.keyboards.projects import (
    PROJECTS_PER_PAGE,
    get_projects_keyboard,
)


def make_projects(
    count: int,
):
    return [
        SimpleNamespace(
            id=index,
            number=index,
            title=f"Project {index}",
            status="available",
        )
        for index in range(
            1,
            count + 1,
        )
    ]


def test_projects_per_page_is_eight():
    assert PROJECTS_PER_PAGE == 8


def test_first_project_page_contains_eight_projects():
    keyboard = get_projects_keyboard(
        projects=make_projects(16),
        course_slug="start",
        page=0,
    )

    project_rows = (
        keyboard.inline_keyboard[:8]
    )

    assert len(project_rows) == 8

    assert (
        project_rows[0][0].callback_data
        == "project:open:1"
    )

    assert (
        project_rows[-1][0].callback_data
        == "project:open:8"
    )


def test_second_project_page_contains_next_projects():
    keyboard = get_projects_keyboard(
        projects=make_projects(16),
        course_slug="start",
        page=1,
    )

    project_rows = (
        keyboard.inline_keyboard[:8]
    )

    assert (
        project_rows[0][0].callback_data
        == "project:open:9"
    )

    assert (
        project_rows[-1][0].callback_data
        == "project:open:16"
    )


def test_single_page_has_no_page_navigation():
    keyboard = get_projects_keyboard(
        projects=make_projects(5),
        course_slug="start",
        page=0,
    )

    assert len(
        keyboard.inline_keyboard
    ) == 6