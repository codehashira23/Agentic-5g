"""Helper: write a fixture to disk for replay testing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def write_fixture(
    fixtures_dir: Path,
    system: str,
    messages: list[dict],
    tools: list[dict],
    response: dict,
    model: str = "",
) -> str:
    payload = json.dumps(
        {"system": system, "messages": messages, "tools": tools, "model": model},
        sort_keys=True,
    )
    key = hashlib.sha256(payload.encode()).hexdigest()[:16]
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    (fixtures_dir / f"{key}.json").write_text(
        json.dumps(response, indent=2), encoding="utf-8"
    )
    return key
