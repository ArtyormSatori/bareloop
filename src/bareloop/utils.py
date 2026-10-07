import json

import yaml


def _parser_formatter(raw):
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, parts[2].strip()


def normalize_tool_call(tool):
    return {
        "id": tool.id,
        "name": tool.function.name,
        "arguments": json.loads(tool.function.arguments),
    }


def _format_bash_result(output, exit_code):
    if exit_code in [0, None]:
        return output
    return f"Error: 后台任务执行失败{exit_code}"


def format_team_events(msgs: list[dict]) -> str:
    lines = []
    for msg in msgs:
        metadata = msg.get("metadata", {})
        request_id = metadata.get("request_id")
        suffix = f" request_id={request_id}" if request_id else ""
        lines.append(f"[{msg['type']}{suffix}] {msg['from']}: {msg['content']}")
    return "[Team events]\n" + "\n".join(lines)


def retry_with_backoff(
    fn,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    multiplier: float = 2.0,
    max_delay: float = 10.0,
    sleep_fn=None,
):
    """Retries transient provider errors with exponential backoff."""
    import time

    from openai import APIConnectionError, InternalServerError, RateLimitError

    sleep = sleep_fn if sleep_fn is not None else time.sleep
    delay = initial_delay
    transient_errors = (RateLimitError, APIConnectionError, InternalServerError)

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except transient_errors:
            if attempt >= max_retries:
                raise
            sleep(delay)
            delay = min(delay * multiplier, max_delay)
        except Exception:
            raise
