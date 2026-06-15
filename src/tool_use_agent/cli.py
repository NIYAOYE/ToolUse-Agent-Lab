import argparse
from collections.abc import Iterable, Iterator
import json
from typing import Any

import httpx


def run_chat(
    client: httpx.Client,
    *,
    session_id: str | None,
    input_lines: Iterable[str] | None = None,
) -> None:
    active_session = session_id or _create_session(client)
    print(f"Session: {active_session}")
    print("Type /quit to exit.")

    lines = input_lines if input_lines is not None else _interactive_lines()
    for raw_message in lines:
        message = raw_message.strip()
        if message == "/quit":
            break
        if not message:
            continue

        received_delta = False
        with client.stream(
            "POST",
            "/v1/chat/stream",
            json={"session_id": active_session, "message": message},
        ) as response:
            response.raise_for_status()
            for event, payload in _iter_sse(response.iter_lines()):
                if event == "model_delta":
                    print(payload.get("text", ""), end="", flush=True)
                    received_delta = True
                elif event == "tool_start":
                    print(f"[tool] starting {payload.get('tool', 'unknown')}")
                elif event == "tool_result":
                    print(f"[tool] completed {payload.get('tool', 'unknown')}")
                elif event == "tool_error":
                    code = (
                        payload.get("result", {})
                        .get("error", {})
                        .get("code", "tool_error")
                    )
                    print(
                        f"[tool] failed {payload.get('tool', 'unknown')}: {code}"
                    )
                elif event == "message_end":
                    if received_delta:
                        print()
                    else:
                        print(payload.get("answer", ""))
                elif event == "error":
                    print(f"[error] {payload.get('message', 'stream failed')}")


def _create_session(client: httpx.Client) -> str:
    response = client.post("/v1/sessions")
    response.raise_for_status()
    return str(response.json()["id"])


def _interactive_lines() -> Iterator[str]:
    while True:
        try:
            yield input("> ")
        except (EOFError, KeyboardInterrupt):
            yield "/quit"
            return


def _iter_sse(lines: Iterable[str]) -> Iterator[tuple[str, dict[str, Any]]]:
    event_name = "message"
    data_lines: list[str] = []
    for line in lines:
        if line == "":
            if data_lines:
                yield event_name, json.loads("\n".join(data_lines))
            event_name = "message"
            data_lines = []
        elif line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())
    if data_lines:
        yield event_name, json.loads("\n".join(data_lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="ToolUse Agent terminal client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--session-id")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=None) as client:
        run_chat(client, session_id=args.session_id)


if __name__ == "__main__":
    main()
