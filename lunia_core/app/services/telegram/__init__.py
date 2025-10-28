from typing import Optional

_AVAILABLE = False
_REASON: Optional[str] = None

try:
    import aiogram  # noqa: F401
    _AVAILABLE = True
except Exception as e:
    _AVAILABLE = False
    _REASON = str(e)

def is_available() -> bool:
    return _AVAILABLE

def reason_unavailable() -> Optional[str]:
    return None if _AVAILABLE else (_REASON or "aiogram not installed")
