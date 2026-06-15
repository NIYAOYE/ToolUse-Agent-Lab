import ast
import os
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter
from typing import Any

from tool_use_agent.tools.contracts import ToolError, ToolResult


_ALLOWED_IMPORTS = {
    "collections",
    "datetime",
    "itertools",
    "json",
    "math",
    "random",
    "re",
    "statistics",
}
_BLOCKED_ROOTS = {
    "ctypes",
    "multiprocessing",
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "sys",
}
_BLOCKED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}
_ENVIRONMENT_KEYS = {
    "COMSPEC",
    "NUMBER_OF_PROCESSORS",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
}


class _PythonPolicy(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violation: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_import(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            self.violation = "relative imports"
        elif node.module:
            self._check_import(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in _BLOCKED_CALLS:
            self.violation = node.func.id
        elif isinstance(node.func, ast.Attribute):
            root = self._attribute_root(node.func)
            if root in _BLOCKED_ROOTS:
                self.violation = root
        self.generic_visit(node)

    def _check_import(self, module_name: str) -> None:
        root = module_name.split(".", maxsplit=1)[0]
        if root not in _ALLOWED_IMPORTS:
            self.violation = root

    @staticmethod
    def _attribute_root(node: ast.Attribute) -> str | None:
        value: ast.expr = node
        while isinstance(value, ast.Attribute):
            value = value.value
        return value.id if isinstance(value, ast.Name) else None


class PythonExecTool:
    name = "python_exec"
    description = "Run restricted Python code in a temporary subprocess."
    args_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python source code to execute.",
            }
        },
        "required": ["code"],
    }

    def __init__(
        self,
        python_executable: str,
        *,
        timeout_seconds: float = 5,
        max_output_chars: int = 12_000,
    ) -> None:
        self._python_executable = str(Path(python_executable).resolve())
        self._timeout_seconds = max(0.01, float(timeout_seconds))
        self._max_output_chars = max(1, int(max_output_chars))

    def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        started_at = perf_counter()
        code = str(arguments.get("code", ""))

        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as exc:
            location = f"line {exc.lineno}" if exc.lineno else "unknown line"
            return self._error(
                "python_syntax_error",
                f"Python syntax error at {location}.",
                started_at,
            )

        policy = _PythonPolicy()
        policy.visit(tree)
        if policy.violation:
            return self._error(
                "forbidden_python",
                f"Python operation '{policy.violation}' is not allowed.",
                started_at,
            )

        with tempfile.TemporaryDirectory(prefix="tool-use-agent-") as temp_dir:
            script_path = Path(temp_dir) / "main.py"
            script_path.write_text(code, encoding="utf-8")
            try:
                completed = subprocess.run(
                    [self._python_executable, "-I", str(script_path)],
                    cwd=temp_dir,
                    env=self._minimal_environment(),
                    shell=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=self._timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                stdout = self._normalize_timeout_output(exc.stdout)
                stderr = self._normalize_timeout_output(exc.stderr)
                return ToolResult(
                    success=False,
                    data={
                        "stdout": self._truncate(stdout)[0],
                        "stderr": self._truncate(stderr)[0],
                        "return_code": None,
                    },
                    error=ToolError(
                        code="python_timeout",
                        message=(
                            "Python execution exceeded the configured "
                            "time limit."
                        ),
                    ),
                    metadata={
                        "duration_ms": self._duration_ms(started_at),
                        "timeout_seconds": self._timeout_seconds,
                    },
                )
            except OSError:
                return self._error(
                    "python_process_error",
                    "Python subprocess could not be started.",
                    started_at,
                )

        stdout, stdout_truncated = self._truncate(completed.stdout)
        stderr, stderr_truncated = self._truncate(completed.stderr)
        data = {
            "stdout": stdout,
            "stderr": stderr,
            "return_code": completed.returncode,
        }
        metadata = {
            "duration_ms": self._duration_ms(started_at),
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }

        if completed.returncode != 0:
            return ToolResult(
                success=False,
                data=data,
                error=ToolError(
                    code="python_execution_error",
                    message="Python execution returned a non-zero exit code.",
                ),
                metadata=metadata,
            )
        return ToolResult(success=True, data=data, metadata=metadata)

    def _truncate(self, value: str) -> tuple[str, bool]:
        if len(value) <= self._max_output_chars:
            return value, False
        return value[: self._max_output_chars], True

    @staticmethod
    def _normalize_timeout_output(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    @staticmethod
    def _minimal_environment() -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key.upper() in _ENVIRONMENT_KEYS
        }

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)

    def _error(
        self,
        code: str,
        message: str,
        started_at: float,
    ) -> ToolResult:
        return ToolResult(
            success=False,
            error=ToolError(code=code, message=message),
            metadata={"duration_ms": self._duration_ms(started_at)},
        )
