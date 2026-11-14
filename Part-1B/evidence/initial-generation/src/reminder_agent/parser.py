"""Extracts the single JSON object from the model's reply (FR-014)."""

import json
import re

FENCE = re.compile(r"```(?:json)?[ \t]*\n(.*)\n```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> dict:
    """Return the JSON object in ``text``; raise ValueError for anything else."""
    stripped = text.strip()
    fenced = FENCE.fullmatch(stripped)
    if fenced:
        stripped = fenced.group(1).strip()
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("the reply is not a JSON object")
    return value
