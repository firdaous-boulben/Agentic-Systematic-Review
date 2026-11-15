import csv
import os
import time
import threading
from pathlib import Path
from datetime import datetime, timezone

from langchain_core.callbacks import BaseCallbackHandler


# Where token usage will be saved
LOG_PATH = Path(__file__).resolve().parents[1] / "data" / "token_usage.csv"

COLUMNS = [
    "timestamp",
    "run_label",
    "agent",
    "model",
    "status",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "duration_seconds",
    "error"
]

WRITE_LOCK = threading.Lock()


class GroqTokenTracker(BaseCallbackHandler):

    def __init__(self, agent, model):
        super().__init__()
        self.agent = agent
        self.model = model
        self.start_times = {}
        self.lock = threading.Lock()

    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        with self.lock:
            self.start_times[str(run_id)] = time.perf_counter()

    def on_llm_start(self, serialized, prompts, *, run_id, **kwargs):
        with self.lock:
            self.start_times.setdefault(str(run_id), time.perf_counter())

    def get_duration(self, run_id):
        with self.lock:
            start = self.start_times.pop(str(run_id), None)

        if start is None:
            return ""

        return round(time.perf_counter() - start, 3)

    def save(self, status, input_tokens, output_tokens,
             total_tokens, duration, error=""):

        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_label": os.getenv("TOKEN_RUN_LABEL", "unlabeled"),
            "agent": self.agent,
            "model": self.model,
            "status": status,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "duration_seconds": duration,
            "error": error
        }

        try:
            with WRITE_LOCK:
                LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

                new_file = (
                    not LOG_PATH.exists()
                    or LOG_PATH.stat().st_size == 0
                )

                with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=COLUMNS)

                    if new_file:
                        writer.writeheader()

                    writer.writerow(row)

        except OSError as e:
            print(f"Token tracking warning: {e}")

    def on_llm_end(self, response, *, run_id, **kwargs):

        duration = self.get_duration(run_id)

        input_tokens = None
        output_tokens = None
        total_tokens = None

        try:
            message = response.generations[0][0].message

            # Preferred: LangChain normalized usage
            usage = getattr(message, "usage_metadata", None) or {}

            if "input_tokens" in usage:
                input_tokens = int(usage["input_tokens"])
                output_tokens = int(usage["output_tokens"])
                total_tokens = int(
                    usage.get(
                        "total_tokens",
                        input_tokens + output_tokens
                    )
                )

            else:
                # Fallback: Groq / OpenAI-compatible metadata
                metadata = getattr(message, "response_metadata", {}) or {}
                llm_output = getattr(response, "llm_output", {}) or {}

                usage = (
                    metadata.get("token_usage")
                    or metadata.get("usage")
                    or llm_output.get("token_usage")
                    or llm_output.get("usage")
                    or {}
                )

                if "prompt_tokens" in usage:
                    input_tokens = int(usage["prompt_tokens"])
                    output_tokens = int(usage["completion_tokens"])
                    total_tokens = int(
                        usage.get(
                            "total_tokens",
                            input_tokens + output_tokens
                        )
                    )

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            pass

        status = (
            "success"
            if total_tokens is not None
            else "usage_unavailable"
        )

        self.save(
            status=status,
            input_tokens="" if input_tokens is None else input_tokens,
            output_tokens="" if output_tokens is None else output_tokens,
            total_tokens="" if total_tokens is None else total_tokens,
            duration=duration
        )

    def on_llm_error(self, error, *, run_id, **kwargs):

        duration = self.get_duration(run_id)

        self.save(
            status="error",
            input_tokens="",
            output_tokens="",
            total_tokens="",
            duration=duration,
            error=type(error).__name__
        )