import sys

from tool_use_agent.tools.python_exec import PythonExecTool


def test_executes_simple_python():
    result = PythonExecTool(sys.executable, timeout_seconds=2).invoke(
        {"code": "print(sum([1, 2, 3]))"}
    )

    assert result.success is True
    assert result.data == {"stdout": "6\n", "stderr": "", "return_code": 0}


def test_allows_safe_standard_library_import():
    result = PythonExecTool(sys.executable, timeout_seconds=2).invoke(
        {"code": "import math\nprint(math.sqrt(81))"}
    )

    assert result.success is True
    assert result.data["stdout"] == "9.0\n"


def test_rejects_dangerous_import():
    result = PythonExecTool(sys.executable).invoke(
        {"code": "import subprocess"}
    )

    assert result.error.code == "forbidden_python"
    assert "subprocess" in result.error.message


def test_rejects_open_call():
    result = PythonExecTool(sys.executable).invoke(
        {"code": "open('x.txt', 'w')"}
    )

    assert result.error.code == "forbidden_python"
    assert "open" in result.error.message


def test_reports_syntax_error_without_starting_process():
    result = PythonExecTool(sys.executable).invoke(
        {"code": "def broken(:\n    pass"}
    )

    assert result.error.code == "python_syntax_error"
    assert result.data is None


def test_reports_non_zero_exit_and_stderr():
    result = PythonExecTool(sys.executable, timeout_seconds=2).invoke(
        {"code": "print('before')\nraise RuntimeError('boom')"}
    )

    assert result.success is False
    assert result.error.code == "python_execution_error"
    assert result.data["stdout"] == "before\n"
    assert "RuntimeError: boom" in result.data["stderr"]
    assert result.data["return_code"] == 1


def test_times_out():
    result = PythonExecTool(sys.executable, timeout_seconds=0.1).invoke(
        {"code": "while True:\n    pass"}
    )

    assert result.error.code == "python_timeout"
    assert result.metadata["timeout_seconds"] == 0.1


def test_truncates_large_output():
    result = PythonExecTool(
        sys.executable,
        timeout_seconds=2,
        max_output_chars=20,
    ).invoke({"code": "print('x' * 100)"})

    assert result.success is True
    assert result.data["stdout"] == "x" * 20
    assert result.metadata["stdout_truncated"] is True
