import asyncio
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.database.models.hint import Hint
from app.database.models.project import Project
from app.database.repositories.course_repository import (
    CourseRepository,
)
from app.database.repositories.project_repository import (
    ProjectRepository,
)
from app.database.session import (
    async_session_factory,
    engine,
)

MINI_CASINO_REQUIREMENTS = """
Обязательные критерии для PASS:

1. В начале программы баланс игрока равен 1000.
2. Пользователь может вводить размер ставки.
3. Ставка должна проходить проверку:
   - ставка должна быть больше 0;
   - ставка не должна превышать текущий баланс;
   - некорректный ввод не должен ломать программу.
4. Результат раунда определяется случайным образом: победа или поражение.
5. При победе баланс увеличивается на размер ставки.
6. При поражении баланс уменьшается на размер ставки.
7. После каждого раунда пользователь видит результат раунда и текущий баланс.
8. Игра поддерживает несколько раундов, а не завершается после первой ставки.
9. Пользователь может вручную выйти из игры.
10. Если баланс становится равен 0, игра автоматически завершается.
11. После завершения показывается финальная статистика:
    - количество сыгранных раундов;
    - количество побед;
    - количество поражений;
    - максимальный баланс за игру;
    - итоговый баланс.
12. Программа не должна содержать критических ошибок,
мешающих основному игровому сценарию.

PASS ставится только если выполнены все обязательные критерии.

Не считать обязательными:
- EASY / MEDIUM / HARD;
- SECRET HIGH RISK;
- Challenges;
- дополнительные бонусные механики.
""".strip()


SMART_FILE_SORTER_REQUIREMENTS = """
Обязательные критерии для PASS:

1. Программа получает от пользователя путь к папке,
которую нужно отсортировать.
2. Программа обрабатывает файлы внутри указанной папки.
3. Уже существующие подпапки не должны сортироваться
как обычные файлы и перемещаться.
4. Для каждого файла определяется его расширение.
5. Программа создаёт нужные папки-категории,
если они ещё не существуют.
6. Файлы перемещаются в соответствующие категории.

Обязательные категории:

Images:
- .jpg
- .jpeg
- .png
- .gif

Videos:
- .mp4
- .mov
- .avi

Documents:
- .pdf
- .txt
- .docx

Archives:
- .zip
- .rar
- .7z

Other:
- любые остальные расширения.

7. Файлы с неизвестными расширениями должны попадать в Other.
8. Файлы должны действительно перемещаться
в соответствующие папки.
9. Основной сценарий программы не должен содержать
критических ошибок.

PASS ставится только если выполнены все обязательные критерии.

Challenges и бонусные возможности обязательными не считать.
""".strip()


async def seed() -> None:
    async with async_session_factory() as session:
        course_repository = CourseRepository(session)

        demo = await course_repository.get_by_slug("demo")

        if demo is None:
            raise RuntimeError(
                "Demo course не найден. Сначала выполни alembic upgrade head."
            )

        now = datetime.now(timezone.utc)

        projects = [
            {
                "course_id": demo.id,
                "number": 1,
                "title": "Mini Casino 🎰",
                "max_xp": 100,
                "ai_requirements": MINI_CASINO_REQUIREMENTS,
                "published_at": now,
            },
            {
                "course_id": demo.id,
                "number": 2,
                "title": "Smart File Sorter 📁",
                "max_xp": 100,
                "ai_requirements": SMART_FILE_SORTER_REQUIREMENTS,
                "published_at": now,
            },
            {
                "course_id": demo.id,
                "number": 3,
                "title": "Backend Web App 🌐",
                "max_xp": 100,
                "ai_requirements": None,
                "published_at": None,
            },
        ]

        for project in projects:
            statement = (
                insert(Project)
                .values(**project)
                .on_conflict_do_update(
                    index_elements=[
                        Project.course_id,
                        Project.number,
                    ],
                    set_={
                        "title": project["title"],
                        "max_xp": project["max_xp"],
                        "ai_requirements": project["ai_requirements"],
                    },
                )
            )

            await session.execute(statement)

        await session.commit()

        project_repository = ProjectRepository(session)

        demo_projects = await project_repository.get_by_course(demo.id)

        projects_by_number = {project.number: project for project in demo_projects}

        hints = [
            # Mini Casino
            {
                "project_id": projects_by_number[1].id,
                "number": 1,
                "xp_after_publish": 80,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[1].id,
                "number": 2,
                "xp_after_publish": 60,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[1].id,
                "number": 3,
                "xp_after_publish": 40,
                "published_at": now,
            },
            # Smart File Sorter
            {
                "project_id": projects_by_number[2].id,
                "number": 1,
                "xp_after_publish": 80,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[2].id,
                "number": 2,
                "xp_after_publish": 60,
                "published_at": now,
            },
            {
                "project_id": projects_by_number[2].id,
                "number": 3,
                "xp_after_publish": 40,
                "published_at": now,
            },
            # Backend Web App
            {
                "project_id": projects_by_number[3].id,
                "number": 1,
                "xp_after_publish": 80,
                "published_at": None,
            },
            {
                "project_id": projects_by_number[3].id,
                "number": 2,
                "xp_after_publish": 60,
                "published_at": None,
            },
            {
                "project_id": projects_by_number[3].id,
                "number": 3,
                "xp_after_publish": 40,
                "published_at": None,
            },
        ]

        for hint in hints:
            statement = (
                insert(Hint)
                .values(**hint)
                .on_conflict_do_update(
                    index_elements=[
                        Hint.project_id,
                        Hint.number,
                    ],
                    set_={
                        "xp_after_publish": hint["xp_after_publish"],
                    },
                )
            )

            await session.execute(statement)

        await session.commit()


async def main() -> None:
    try:
        await seed()

        print("Initial Demo data created.")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
