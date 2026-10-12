#!/usr/bin/env python3
"""Pre-flight connectivity test for LLM provider credentials.

Validates that GEMINI_API_KEY is configured and can generate responses via LiteLLM.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))


def main() -> int:
    load_env_file(Path(".env"))

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY is not set in environment or .env file.")
        return 1

    import json
    import urllib.request

    import litellm

    print("Fetching active Groq models from API...")
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "curl/8.0",
            },
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            available = [m["id"] for m in data.get("data", []) if "whisper" not in m["id"]]
            print(f"Available text models on Groq: {available}")
    except Exception as exc:
        print(f"Could not list models: {exc}")
        available = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    model = "groq/qwen/qwen3.8-27b"
    print(f"Testing direct connection to {model} via LiteLLM...")
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "Respond with the single word: READY"}],
            api_key=api_key,
        )
        reply = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else "unknown"
        print(f"[SUCCESS] Model {model} responded: {reply}")
        print(f"[SUCCESS] Total tokens used: {tokens}")
        return 0
    except Exception as exc:
        print(f"[FAIL] Model {model} failed: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
