"""Feature catalog loader for Lunia research workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - offline fallback
    yaml = None  # type: ignore

CATALOG_PATH = Path(__file__).resolve().parent.parent / "features.yaml"


class FeatureCatalogError(RuntimeError):
    """Raised when the feature catalog cannot be parsed."""


class FeatureCatalog:
    def __init__(self, catalog_path: Path | None = None) -> None:
        self.catalog_path = catalog_path or CATALOG_PATH
        self._raw: Dict[str, object] | None = None

    def load(self) -> Dict[str, object]:
        if self._raw is None:
            if not self.catalog_path.exists():
                raise FeatureCatalogError(
                    f"feature catalog missing: {self.catalog_path}"
                )
            with self.catalog_path.open("r", encoding="utf-8") as handle:
                text = handle.read()
            data = self._parse_yaml(text)
            if "features" not in data:
                raise FeatureCatalogError("feature catalog missing 'features' root key")
            self._raw = data["features"]
        return self._raw

    def _parse_yaml(self, text: str) -> Dict[str, object]:
        if yaml is not None:
            loaded = yaml.safe_load(text) or {}
            if not isinstance(loaded, dict):
                raise FeatureCatalogError("feature catalog must decode to a dictionary")
            return loaded
        stripped = (text or "").lstrip()
        if stripped.startswith("{"):
            try:
                loaded = json.loads(text or "{}")
                if not isinstance(loaded, dict):
                    raise ValueError
                return loaded
            except ValueError as exc:  # pragma: no cover - defensive path
                raise FeatureCatalogError(
                    "failed to parse feature catalog without PyYAML"
                ) from exc
        # Minimal YAML parser for mapping/list combinations used in tests.
        result: Dict[str, object] = {}
        stack: List[tuple[int, object]] = [(-1, result)]
        for raw_line in (text or "").splitlines():
            if not raw_line.strip() or raw_line.strip().startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            stripped_line = raw_line.strip()
            while stack and indent <= stack[-1][0]:
                stack.pop()
            if not stack:
                stack.append((-1, result))
            parent = stack[-1][1]
            if stripped_line.startswith("- "):
                if not isinstance(parent, list):
                    raise FeatureCatalogError(
                        "invalid YAML structure: list item without list"
                    )
                value_part = stripped_line[2:].strip()
                if not value_part:
                    item: object = {}
                elif ":" in value_part:
                    key, value = [
                        segment.strip() for segment in value_part.split(":", 1)
                    ]
                    item = {key: _coerce_scalar(value)}
                else:
                    item = _coerce_scalar(value_part)
                parent.append(item)
                if isinstance(item, dict):
                    stack.append((indent, item))
                continue
            if ":" not in stripped_line:
                continue
            key, value = [segment.strip() for segment in stripped_line.split(":", 1)]
            container = parent
            if isinstance(container, list):
                raise FeatureCatalogError(
                    "invalid YAML structure: mapping under list without item"
                )
            if value == "":
                new_container: Dict[str, object] = {}
                container[key] = new_container
                stack.append((indent, new_container))
            elif value == "[]":
                new_list: list[object] = []
                container[key] = new_list
                stack.append((indent, new_list))
            elif value == "{}":
                new_container = {}
                container[key] = new_container
                stack.append((indent, new_container))
            else:
                container[key] = _coerce_scalar(value)
        return result

    def list_features(self) -> List[str]:
        return list(self.load().keys())

    def describe(self, name: str) -> Dict[str, object]:
        features = self.load()
        if name not in features:
            raise FeatureCatalogError(f"feature '{name}' not found")
        return features[name]

    def to_json(self) -> str:
        return json.dumps(self.load(), indent=2, sort_keys=True)


def ensure_feature(name: str) -> Dict[str, object]:
    catalog = FeatureCatalog()
    return catalog.describe(name)


def _coerce_scalar(value: str) -> object:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1]
        return [item.strip() for item in inner.split(",") if item.strip()]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
