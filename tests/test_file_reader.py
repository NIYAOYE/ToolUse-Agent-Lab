from pathlib import Path

import pytest

from tool_use_agent.tools.file_reader import FileReaderTool


def test_reads_utf8_file_inside_workspace(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "notes.txt").write_text("hello", encoding="utf-8")

    result = FileReaderTool(root, max_bytes=100).invoke(
        {"path": "notes.txt"}
    )

    assert result.success is True
    assert result.data == {
        "path": "notes.txt",
        "content": "hello",
        "encoding": "utf-8",
        "byte_count": 5,
    }
    assert result.metadata["truncated"] is False


def test_reads_gb18030_file_inside_workspace(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "notes.txt").write_bytes("中文内容".encode("gb18030"))

    result = FileReaderTool(root).invoke({"path": "notes.txt"})

    assert result.success is True
    assert result.data["content"] == "中文内容"
    assert result.data["encoding"] == "gb18030"


def test_rejects_parent_traversal(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()

    result = FileReaderTool(root).invoke({"path": "../secret.txt"})

    assert result.error.code == "path_outside_workspace"


def test_rejects_absolute_path(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()

    result = FileReaderTool(root).invoke(
        {"path": str((tmp_path / "secret.txt").resolve())}
    )

    assert result.error.code == "absolute_path_forbidden"


def test_rejects_binary_file(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "data.bin").write_bytes(b"abc\x00def")

    result = FileReaderTool(root).invoke({"path": "data.bin"})

    assert result.error.code == "binary_file_forbidden"


def test_rejects_oversized_file(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "large.txt").write_text("12345", encoding="utf-8")

    result = FileReaderTool(root, max_bytes=4).invoke(
        {"path": "large.txt"}
    )

    assert result.error.code == "file_too_large"


def test_rejects_symlink_escape(tmp_path: Path):
    root = tmp_path / "workspace"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret", encoding="utf-8")
    link = root / "link.txt"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows account")

    result = FileReaderTool(root).invoke({"path": "link.txt"})

    assert result.error.code == "path_outside_workspace"
