import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class PythonSyntaxCheckResult:
    valid: bool
    error_message: str | None = None
    line: int | None = None
    column: int | None = None


def validate_python_syntax(
    source_code: str,
) -> PythonSyntaxCheckResult:
    try:
        ast.parse(
            source_code,
            filename="<student_solution>",
            mode="exec",
        )

    except SyntaxError as error:
        return PythonSyntaxCheckResult(
            valid=False,
            error_message=(
                error.msg
                or "Синтаксическая ошибка"
            ),
            line=error.lineno,
            column=error.offset,
        )

    return PythonSyntaxCheckResult(
        valid=True
    )