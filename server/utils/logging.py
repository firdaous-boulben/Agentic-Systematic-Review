
from datetime import datetime, timezone


def add_execution_logs(existing_logs, messages):
    if isinstance(messages, str):
        messages = [messages]

    new_logs = [
        {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(
                timespec="seconds"
            )
        }
        for message in messages
    ]

    return [*(existing_logs or []), *new_logs]