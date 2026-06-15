from pathlib import Path
from time import perf_counter
from typing import Any

from tool_use_agent.tools.contracts import ToolError, ToolResult


class FileReaderTool:
    name = "read_file"
    description = "Read a text file located inside the configured workspace."
    args_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path relative to the configured workspace.",
            }
        },
        "required": ["path"],
    }

    def __init__(self, workspace_root: Path, *, max_bytes: int = 1_000_000):
        self._workspace_root = workspace_root.resolve()
        self._max_bytes = max(1, int(max_bytes))

    def invoke(self, arguments: dict[str, Any]) -> ToolResult:
        started_at = perf_counter()
        raw_path = str(arguments.get("path", "")).strip()
        requested_path = Path(raw_path)

        if not raw_path:
            return self._error(
                "invalid_file_path",
                "File path must not be empty.",
                started_at,
            )
        if requested_path.is_absolute():
            return self._error(
                "absolute_path_forbidden",
                "File path must be relative to the workspace.",
                started_at,
            )

        try:
            target = (self._workspace_root / requested_path).resolve(
                strict=False
            )
        except (OSError, RuntimeError):
            return self._error(
                "invalid_file_path",
                "File path could not be resolved.",
                started_at,
            )

        if not target.is_relative_to(self._workspace_root):
            return self._error(
                "path_outside_workspace",
                "File path resolves outside the workspace.",
                started_at,
            )

        try:
            target = target.resolve(strict=True)
        except FileNotFoundError:
            return self._error(
                "file_not_found",
                "The requested file does not exist.",
                started_at,
            )
        except (OSError, RuntimeError):
            return self._error(
                "file_read_error",
                "The requested file could not be accessed.",
                started_at,
            )

        if not target.is_relative_to(self._workspace_root):
            return self._error(
                "path_outside_workspace",
                "File path resolves outside the workspace.",
                started_at,
            )
        if not target.is_file():
            return self._error(
                "not_a_file",
                "The requested path is not a regular file.",
                started_at,
            )

        try:
            byte_count = target.stat().st_size
            if byte_count > self._max_bytes:
                return self._error(
                    "file_too_large",
                    f"File exceeds the {self._max_bytes}-byte limit.",
                    started_at,
                )
            content_bytes = target.read_bytes()
        except OSError:
            return self._error(
                "file_read_error",
                "The requested file could not be read.",
                started_at,
            )

        if b"\x00" in content_bytes:
            return self._error(
                "binary_file_forbidden",
                "Binary files are not supported.",
                started_at,
            )

        decoded = self._decode_text(content_bytes)
        if decoded is None:
            return self._error(
                "unsupported_text_encoding",
                "File is not valid UTF-8 or GB18030 text.",
                started_at,
            )
        content, encoding = decoded

        return ToolResult(
            success=True,
            data={
                "path": target.relative_to(self._workspace_root).as_posix(),
                "content": content,
                "encoding": encoding,
                "byte_count": byte_count,
            },
            metadata={
                "duration_ms": self._duration_ms(started_at),
                "truncated": False,
            },
        )

    @staticmethod
    def _decode_text(content: bytes) -> tuple[str, str] | None:
        if content.startswith(b"\xef\xbb\xbf"):
            return content.decode("utf-8-sig"), "utf-8-sig"
        try:
            return content.decode("utf-8"), "utf-8"
        except UnicodeDecodeError:
            try:
                return content.decode("gb18030"), "gb18030"
            except UnicodeDecodeError:
                return None

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
