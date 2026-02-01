from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

_LABELS: Dict[str, str] | None = None


def _labels_path() -> Path:
    return Path(__file__).resolve().parent / "labels.txt"


def _load_labels() -> Dict[str, str]:
    path = _labels_path()
    if not path.exists():
        return {}
    mapping: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        mapping[key.strip()] = value.strip()
    return mapping


def tr(key: str, **kwargs: object) -> str:
    global _LABELS
    if _LABELS is None:
        _LABELS = _load_labels()
    text = _LABELS.get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def states_display(prefix: str, values: Iterable[str]) -> list[str]:
    return [state_display(prefix, value) for value in values]


def state_display(prefix: str, value: str) -> str:
    global _LABELS
    if _LABELS is None:
        _LABELS = _load_labels()
    return _LABELS.get(f"{prefix}.{value}", value)


def state_to_physical(prefix: str, display_value: str, fallback: str) -> str:
    global _LABELS
    if _LABELS is None:
        _LABELS = _load_labels()
    lookup = {tr(f"{prefix}.{fallback}"): fallback, fallback: fallback}
    for key, value in _LABELS.items():
        if key.startswith(f"{prefix}."):
            physical = key.split(".", 1)[1]
            lookup[value] = physical
    return lookup.get(display_value, fallback)
