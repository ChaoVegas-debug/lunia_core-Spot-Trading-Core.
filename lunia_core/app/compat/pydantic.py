"""Compatibility layer for optional pydantic dependency."""

from __future__ import annotations

import importlib
from typing import Any, Dict

HAVE_PYDANTIC = False
try:
    _pydantic = importlib.import_module("pydantic")
    BaseModel = _pydantic.BaseModel  # type: ignore[attr-defined]
    Field = _pydantic.Field  # type: ignore[attr-defined]
    ValidationError = _pydantic.ValidationError  # type: ignore[attr-defined]
    root_validator = _pydantic.root_validator  # type: ignore[attr-defined]

    HAVE_PYDANTIC = True
except Exception:  # pragma: no cover - executed only when pydantic missing

    class ValidationError(Exception):
        """Fallback validation error when pydantic is unavailable."""

    def Field(default=None, **kwargs):  # type: ignore[override]
        return default

    def root_validator(*args, **kwargs):  # type: ignore[override]
        def _decorator(fn):
            return fn

        return _decorator

    class BaseModel:
        """Minimal BaseModel shim with dict-like behaviour."""

        def __init__(self, **data: Any) -> None:
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self, *_, **__):  # type: ignore[override]
            return {k: v for k, v in self.__dict__.items()}

        def model_dump(self, *_, **__):  # type: ignore[override]
            return self.dict()

        @classmethod
        def parse_obj(cls, obj: Dict[str, Any]):  # type: ignore[override]
            if not isinstance(obj, dict):
                raise ValidationError("Expected dict")
            return cls(**obj)


__all__ = [
    "BaseModel",
    "Field",
    "ValidationError",
    "root_validator",
    "HAVE_PYDANTIC",
]
