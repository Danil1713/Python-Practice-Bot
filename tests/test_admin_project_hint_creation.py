import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.handlers import admin_post_creation
from app.bot.states.admin import AdminScheduleStates
from app.database.models.course import Course
from app.database.models.hint import Hint
from app.database.models.project import Project
from app.database.repositories.hint_repository import (
    HintRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.session import async_session_factory
from app.services.hint_service import (
    HintCreationError,
    create_hint,
)
from app.services.project_service import (
    ProjectCreationError,
    create_project,
)


class FakeFSMContext:
    def __init__(
        self,
        data=None,
        current_state=None,
    ):
        self.data = dict(data or {})
        self.current_state = current_state

    async def get_data(self):
        return dict(self.data)

    async def update_data(
        self,
        **kwargs,
    ):
        self.data.update(kwargs)
        return dict(self.data)

    async def set_state(
        self,
        state,
    ):
        self.current_state = state

    async def clear(self):
        self.data.clear()
        self.current_state = None


@pytest.mark.asyncio
async def test_unpublished_projects_only(
    db_session,
):
    course = Course(
        slug="admin_project_filter",
        title="Admin Project Filter",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    unpublished = Project(
        course_id=course.id,
        number=1,
        title="Unpublished Project",
        max_xp=100,
        ai_requirements="Requirements",
    )

    published = Project(
        course_id=course.id,
        number=2,
        title="Published Project",
        max_xp=100,
        ai_requirements="Requirements",
        published_at=datetime.now(timezone.utc),
    )

    db_session.add_all(
        [
            unpublished,
            published,
        ]
    )

    await db_session.flush()

    repository = ProjectRepository(
        db_session
    )

    projects = (
        await repository
        .get_unpublished_by_course(
            course.id
        )
    )

    assert [
        project.id
        for project in projects
    ] == [
        unpublished.id
    ]


@pytest.mark.asyncio
async def test_project_without_hints_is_available_for_hint(
    db_session,
):
    course = Course(
        slug="admin_hint_no_hints",
        title="Admin Hint No Hints",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    project = Project(
        course_id=course.id,
        number=1,
        title="Project Without Hints",
        max_xp=100,
        ai_requirements="Requirements",
    )

    db_session.add(project)
    await db_session.flush()

    repository = ProjectRepository(
        db_session
    )

    projects = (
        await repository
        .get_available_for_hint_by_course(
            course.id
        )
    )

    assert [
        item.id
        for item in projects
    ] == [
        project.id
    ]


@pytest.mark.asyncio
async def test_project_with_unpublished_hint_is_available(
    db_session,
):
    course = Course(
        slug="admin_hint_unpublished",
        title="Admin Hint Unpublished",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    project = Project(
        course_id=course.id,
        number=1,
        title="Project",
        max_xp=100,
        ai_requirements="Requirements",
    )

    db_session.add(project)
    await db_session.flush()

    hint = Hint(
        project_id=project.id,
        number=1,
        xp_after_publish=80,
    )

    db_session.add(hint)
    await db_session.flush()

    repository = ProjectRepository(
        db_session
    )

    projects = (
        await repository
        .get_available_for_hint_by_course(
            course.id
        )
    )

    assert [
        item.id
        for item in projects
    ] == [
        project.id
    ]


@pytest.mark.asyncio
async def test_project_with_only_published_hints_is_hidden(
    db_session,
):
    course = Course(
        slug="admin_hint_published",
        title="Admin Hint Published",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    project = Project(
        course_id=course.id,
        number=1,
        title="Project",
        max_xp=100,
        ai_requirements="Requirements",
    )

    db_session.add(project)
    await db_session.flush()

    hint = Hint(
        project_id=project.id,
        number=1,
        xp_after_publish=80,
        published_at=datetime.now(timezone.utc),
    )

    db_session.add(hint)
    await db_session.flush()

    repository = ProjectRepository(
        db_session
    )

    projects = (
        await repository
        .get_available_for_hint_by_course(
            course.id
        )
    )

    assert projects == []


@pytest.mark.asyncio
async def test_only_unpublished_hints_are_returned(
    db_session,
):
    course = Course(
        slug="admin_hint_filter",
        title="Admin Hint Filter",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    project = Project(
        course_id=course.id,
        number=1,
        title="Project",
        max_xp=100,
        ai_requirements="Requirements",
    )

    db_session.add(project)
    await db_session.flush()

    unpublished = Hint(
        project_id=project.id,
        number=1,
        xp_after_publish=80,
    )

    published = Hint(
        project_id=project.id,
        number=2,
        xp_after_publish=60,
        published_at=datetime.now(timezone.utc),
    )

    db_session.add_all(
        [
            unpublished,
            published,
        ]
    )

    await db_session.flush()

    repository = HintRepository(
        db_session
    )

    hints = (
        await repository
        .get_unpublished_by_project(
            project.id
        )
    )

    assert [
        hint.id
        for hint in hints
    ] == [
        unpublished.id
    ]


@pytest.mark.asyncio
async def test_project_next_number_and_default_xp(
    db_session,
):
    course = Course(
        slug="admin_project_creation",
        title="Admin Project Creation",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    existing_project = Project(
        course_id=course.id,
        number=3,
        title="Existing Project",
        ai_requirements="Existing requirements",
    )

    db_session.add(existing_project)
    await db_session.flush()

    repository = ProjectRepository(
        db_session
    )

    number = await repository.get_next_number(
        course.id
    )

    assert number == 4

    project = await repository.create(
        course_id=course.id,
        number=number,
        title="New Project",
        ai_requirements="New requirements",
    )

    await db_session.flush()

    assert project.number == 4
    assert project.title == "New Project"
    assert project.ai_requirements == (
        "New requirements"
    )
    assert project.max_xp == 100
    assert project.published_at is None
    assert project.telegram_message_id is None


@pytest.mark.asyncio
async def test_first_project_number_is_one(
    db_session,
):
    course = Course(
        slug="admin_first_project",
        title="Admin First Project",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    repository = ProjectRepository(
        db_session
    )

    number = await repository.get_next_number(
        course.id
    )

    assert number == 1


@pytest.mark.asyncio
async def test_hint_next_number_and_xp_values(
    db_session,
):
    course = Course(
        slug="admin_hint_creation",
        title="Admin Hint Creation",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add(course)
    await db_session.flush()

    project = Project(
        course_id=course.id,
        number=1,
        title="Project",
        ai_requirements="Requirements",
    )

    db_session.add(project)
    await db_session.flush()

    repository = HintRepository(
        db_session
    )

    first_number = await repository.get_next_number(
        project.id
    )

    assert first_number == 1

    first_hint = await repository.create(
        project_id=project.id,
        number=first_number,
        xp_after_publish=80,
    )

    await db_session.flush()

    assert first_hint.number == 1
    assert first_hint.xp_after_publish == 80
    assert first_hint.published_at is None
    assert first_hint.telegram_message_id is None

    second_number = await repository.get_next_number(
        project.id
    )

    assert second_number == 2

    second_hint = await repository.create(
        project_id=project.id,
        number=second_number,
        xp_after_publish=60,
    )

    await db_session.flush()

    assert second_hint.number == 2
    assert second_hint.xp_after_publish == 60


@pytest.mark.asyncio
async def test_next_numbers_are_scoped_to_parent(
    db_session,
):
    first_course = Course(
        slug="admin_number_scope_1",
        title="Number Scope 1",
        requires_subscription=False,
        is_active=True,
    )

    second_course = Course(
        slug="admin_number_scope_2",
        title="Number Scope 2",
        requires_subscription=False,
        is_active=True,
    )

    db_session.add_all(
        [
            first_course,
            second_course,
        ]
    )

    await db_session.flush()

    project = Project(
        course_id=first_course.id,
        number=5,
        title="Project",
        ai_requirements="Requirements",
    )

    db_session.add(project)
    await db_session.flush()

    project_repository = ProjectRepository(
        db_session
    )

    assert (
        await project_repository.get_next_number(
            first_course.id
        )
        == 6
    )

    assert (
        await project_repository.get_next_number(
            second_course.id
        )
        == 1
    )


@pytest.mark.asyncio
async def test_create_project_service():
    async with async_session_factory() as session:
        course = Course(
            slug="service_project_creation",
            title="Service Project Creation",
            requires_subscription=False,
            is_active=True,
        )

        session.add(course)
        await session.commit()

    first = await create_project(
        course_slug="service_project_creation",
        title="  First Project  ",
        ai_requirements="  First requirements  ",
    )

    second = await create_project(
        course_slug="service_project_creation",
        title="Second Project",
        ai_requirements="Second requirements",
    )

    assert first.number == 1
    assert first.title == "First Project"

    assert second.number == 2
    assert second.title == "Second Project"

    async with async_session_factory() as session:
        repository = ProjectRepository(
            session
        )

        project = await repository.get_by_id(
            first.id
        )

        assert project is not None
        assert project.course_id == course.id
        assert project.number == 1
        assert project.title == "First Project"
        assert project.ai_requirements == (
            "First requirements"
        )
        assert project.max_xp == 100
        assert project.published_at is None
        assert project.telegram_message_id is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "title",
        "ai_requirements",
    ),
    [
        (
            "",
            "Requirements",
        ),
        (
            "Project",
            "   ",
        ),
    ],
)
async def test_create_project_rejects_invalid_data(
    title,
    ai_requirements,
):
    with pytest.raises(ProjectCreationError):
        await create_project(
            course_slug="does_not_matter",
            title=title,
            ai_requirements=ai_requirements,
        )


@pytest.mark.asyncio
async def test_create_hint_assigns_number_and_xp():
    async with async_session_factory() as session:
        course = Course(
            slug="service_hint_creation",
            title="Service Hint Creation",
            requires_subscription=False,
            is_active=True,
        )

        session.add(course)
        await session.commit()

    project = await create_project(
        course_slug="service_hint_creation",
        title="Project",
        ai_requirements="Requirements",
    )

    first = await create_hint(
        course_slug="service_hint_creation",
        project_id=project.id,
    )

    second = await create_hint(
        course_slug="service_hint_creation",
        project_id=project.id,
    )

    third = await create_hint(
        course_slug="service_hint_creation",
        project_id=project.id,
    )

    assert first.number == 1
    assert first.xp_after_publish == 80

    assert second.number == 2
    assert second.xp_after_publish == 60

    assert third.number == 3
    assert third.xp_after_publish == 40

    with pytest.raises(
        HintCreationError,
        match="Для Hint 4 не настроено значение XP",
    ):
        await create_hint(
            course_slug="service_hint_creation",
            project_id=project.id,
        )

    async with async_session_factory() as session:
        repository = HintRepository(
            session
        )

        hints = await repository.get_by_project(
            project.id
        )

        assert len(hints) == 3

        assert [
            hint.xp_after_publish
            for hint in hints
        ] == [
            80,
            60,
            40,
        ]

        assert all(
            hint.published_at is None
            for hint in hints
        )

        assert all(
            hint.telegram_message_id is None
            for hint in hints
        )


@pytest.mark.asyncio
async def test_create_hint_rejects_project_from_other_course():
    async with async_session_factory() as session:
        first_course = Course(
            slug="hint_context_course_1",
            title="Hint Context 1",
            requires_subscription=False,
            is_active=True,
        )

        second_course = Course(
            slug="hint_context_course_2",
            title="Hint Context 2",
            requires_subscription=False,
            is_active=True,
        )

        session.add_all(
            [
                first_course,
                second_course,
            ]
        )

        await session.commit()

    project = await create_project(
        course_slug="hint_context_course_1",
        title="Project",
        ai_requirements="Requirements",
    )

    with pytest.raises(
        HintCreationError,
        match="Проект не относится к текущему курсу",
    ):
        await create_hint(
            course_slug="hint_context_course_2",
            project_id=project.id,
        )


@pytest.mark.asyncio
async def test_concurrent_project_creation_gets_unique_numbers():
    async with async_session_factory() as session:
        course = Course(
            slug="concurrent_project_creation",
            title="Concurrent Project Creation",
            requires_subscription=False,
            is_active=True,
        )

        session.add(course)
        await session.commit()

    first, second = await asyncio.gather(
        create_project(
            course_slug="concurrent_project_creation",
            title="First Concurrent Project",
            ai_requirements="Requirements 1",
        ),
        create_project(
            course_slug="concurrent_project_creation",
            title="Second Concurrent Project",
            ai_requirements="Requirements 2",
        ),
    )

    assert {
        first.number,
        second.number,
    } == {
        1,
        2,
    }

    assert first.id != second.id


@pytest.mark.asyncio
async def test_concurrent_hint_creation_gets_unique_numbers():
    async with async_session_factory() as session:
        course = Course(
            slug="concurrent_hint_creation",
            title="Concurrent Hint Creation",
            requires_subscription=False,
            is_active=True,
        )

        session.add(course)
        await session.commit()

    project = await create_project(
        course_slug="concurrent_hint_creation",
        title="Project",
        ai_requirements="Requirements",
    )

    first, second = await asyncio.gather(
        create_hint(
            course_slug="concurrent_hint_creation",
            project_id=project.id,
        ),
        create_hint(
            course_slug="concurrent_hint_creation",
            project_id=project.id,
        ),
    )

    assert {
        first.number,
        second.number,
    } == {
        1,
        2,
    }

    assert {
        first.xp_after_publish,
        second.xp_after_publish,
    } == {
        80,
        60,
    }

    assert first.id != second.id


@pytest.mark.asyncio
async def test_project_is_not_created_before_confirmation(
    monkeypatch,
):
    create_project_mock = AsyncMock()

    monkeypatch.setattr(
        admin_post_creation,
        "create_project",
        create_project_mock,
    )

    monkeypatch.setattr(
        admin_post_creation,
        "check_admin",
        AsyncMock(return_value=True),
    )

    monkeypatch.setattr(
        admin_post_creation,
        "is_admin",
        lambda user_id: True,
    )

    state = FakeFSMContext(
        data={
            "course_slug": "python_start",
            "post_type": "project",
        },
        current_state=(
            AdminScheduleStates.choosing_project
        ),
    )

    callback = SimpleNamespace(
        data="admin:create:project",
        message=SimpleNamespace(
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_project_start_handler(
            callback,
            state,
        )
    )

    title_message = SimpleNamespace(
        from_user=SimpleNamespace(
            id=1
        ),
        text="  Новый Project  ",
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_project_title_handler(
            title_message,
            state,
        )
    )

    requirements_message = SimpleNamespace(
        from_user=SimpleNamespace(
            id=1
        ),
        text="  Выполнить все обязательные условия  ",
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_project_requirements_handler(
            requirements_message,
            state,
        )
    )

    create_project_mock.assert_not_awaited()

    assert state.current_state == (
        AdminScheduleStates
        .confirming_project_creation
    )

    assert state.data["project_title"] == (
        "Новый Project"
    )

    assert (
        state.data[
            "project_ai_requirements"
        ]
        == "Выполнить все обязательные условия"
    )


@pytest.mark.asyncio
async def test_project_creation_cancel_returns_to_project_list(
    monkeypatch,
):
    monkeypatch.setattr(
        admin_post_creation,
        "check_admin",
        AsyncMock(return_value=True),
    )

    monkeypatch.setattr(
        admin_post_creation,
        "get_course_projects_for_schedule",
        AsyncMock(return_value=[]),
    )

    state = FakeFSMContext(
        data={
            "course_slug": "python_start",
            "post_type": "project",
            "project_title": "Temporary",
            "project_ai_requirements": (
                "Temporary requirements"
            ),
        },
        current_state=(
            AdminScheduleStates
            .confirming_project_creation
        ),
    )

    callback = SimpleNamespace(
        data="admin:create:project:cancel",
        message=SimpleNamespace(
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_project_cancel_handler(
            callback,
            state,
        )
    )

    assert state.current_state == (
        AdminScheduleStates.choosing_project
    )

    assert state.data == {
        "course_slug": "python_start",
        "post_type": "project",
        "project_id": None,
        "hint_id": None,
    }


@pytest.mark.asyncio
async def test_hint_is_not_created_before_confirmation(
    monkeypatch,
):
    create_hint_mock = AsyncMock()

    monkeypatch.setattr(
        admin_post_creation,
        "create_hint",
        create_hint_mock,
    )

    monkeypatch.setattr(
        admin_post_creation,
        "check_admin",
        AsyncMock(return_value=True),
    )

    state = FakeFSMContext(
        data={
            "course_slug": "python_start",
            "post_type": "hint",
            "project_id": 123,
        },
        current_state=(
            AdminScheduleStates.choosing_hint
        ),
    )

    callback = SimpleNamespace(
        data="admin:create:hint",
        message=SimpleNamespace(
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_hint_start_handler(
            callback,
            state,
        )
    )

    create_hint_mock.assert_not_awaited()

    assert state.current_state == (
        AdminScheduleStates
        .confirming_hint_creation
    )

    assert state.data["course_slug"] == (
        "python_start"
    )

    assert state.data["project_id"] == 123


@pytest.mark.asyncio
async def test_hint_creation_cancel_returns_to_same_project(
    monkeypatch,
):
    monkeypatch.setattr(
        admin_post_creation,
        "check_admin",
        AsyncMock(return_value=True),
    )

    get_hints_mock = AsyncMock(
        return_value=[]
    )

    monkeypatch.setattr(
        admin_post_creation,
        "get_project_hints_for_schedule",
        get_hints_mock,
    )

    state = FakeFSMContext(
        data={
            "course_slug": "python_start",
            "post_type": "hint",
            "project_id": 123,
        },
        current_state=(
            AdminScheduleStates
            .confirming_hint_creation
        ),
    )

    callback = SimpleNamespace(
        data="admin:create:hint:cancel",
        message=SimpleNamespace(
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_hint_cancel_handler(
            callback,
            state,
        )
    )

    get_hints_mock.assert_awaited_once_with(
        123
    )

    assert state.current_state == (
        AdminScheduleStates.choosing_hint
    )

    assert state.data == {
        "course_slug": "python_start",
        "post_type": "hint",
        "project_id": 123,
        "hint_id": None,
    }


@pytest.mark.asyncio
async def test_project_confirmation_creates_once_and_returns_to_list(
    monkeypatch,
):
    created_project = SimpleNamespace(
        id=501,
        number=4,
        title="New Project",
    )

    create_project_mock = AsyncMock(
        return_value=created_project
    )

    monkeypatch.setattr(
        admin_post_creation,
        "create_project",
        create_project_mock,
    )

    monkeypatch.setattr(
        admin_post_creation,
        "check_admin",
        AsyncMock(return_value=True),
    )

    get_projects_mock = AsyncMock(
        return_value=[]
    )

    monkeypatch.setattr(
        admin_post_creation,
        "get_course_projects_for_schedule",
        get_projects_mock,
    )

    state = FakeFSMContext(
        data={
            "course_slug": "python_start",
            "post_type": "project",
            "project_title": "New Project",
            "project_ai_requirements": (
                "Required criteria"
            ),
        },
        current_state=(
            AdminScheduleStates
            .confirming_project_creation
        ),
    )

    callback = SimpleNamespace(
        data="admin:create:project:confirm",
        message=SimpleNamespace(
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_project_confirm_handler(
            callback,
            state,
        )
    )

    create_project_mock.assert_awaited_once_with(
        course_slug="python_start",
        title="New Project",
        ai_requirements="Required criteria",
    )

    get_projects_mock.assert_awaited_once_with(
        "python_start"
    )

    assert state.current_state == (
        AdminScheduleStates.choosing_project
    )

    assert state.data == {
        "course_slug": "python_start",
        "post_type": "project",
        "project_id": None,
        "hint_id": None,
    }

    callback.answer.assert_awaited_once_with(
        "✅ Project 4 создан."
    )


@pytest.mark.asyncio
async def test_hint_confirmation_creates_once_and_returns_to_same_project(
    monkeypatch,
):
    created_hint = SimpleNamespace(
        id=601,
        number=2,
        project_id=123,
        xp_after_publish=60,
    )

    create_hint_mock = AsyncMock(
        return_value=created_hint
    )

    monkeypatch.setattr(
        admin_post_creation,
        "create_hint",
        create_hint_mock,
    )

    monkeypatch.setattr(
        admin_post_creation,
        "check_admin",
        AsyncMock(return_value=True),
    )

    get_hints_mock = AsyncMock(
        return_value=[]
    )

    monkeypatch.setattr(
        admin_post_creation,
        "get_project_hints_for_schedule",
        get_hints_mock,
    )

    state = FakeFSMContext(
        data={
            "course_slug": "python_start",
            "post_type": "hint",
            "project_id": 123,
        },
        current_state=(
            AdminScheduleStates
            .confirming_hint_creation
        ),
    )

    callback = SimpleNamespace(
        data="admin:create:hint:confirm",
        message=SimpleNamespace(
            edit_text=AsyncMock(),
        ),
        answer=AsyncMock(),
    )

    await (
        admin_post_creation
        .admin_create_hint_confirm_handler(
            callback,
            state,
        )
    )

    create_hint_mock.assert_awaited_once_with(
        course_slug="python_start",
        project_id=123,
    )

    get_hints_mock.assert_awaited_once_with(
        123
    )

    assert state.current_state == (
        AdminScheduleStates.choosing_hint
    )

    assert state.data == {
        "course_slug": "python_start",
        "post_type": "hint",
        "project_id": 123,
        "hint_id": None,
    }

    callback.answer.assert_awaited_once_with(
        "✅ Hint 2 создана. "
        "XP после публикации: 60."
    )