"""Pydantic models for the cores API."""

from __future__ import annotations

from typing import Dict, List, Optional

from app.compat.pydantic import BaseModel, Field


class CoreStatus(BaseModel):
    name: str
    status: str
    enabled: bool = True
    weight: float = Field(1.0, ge=0)
    tags: List[str] = Field(default_factory=list)


class ToggleRequest(BaseModel):
    enabled: bool


class WeightRequest(BaseModel):
    weight: float = Field(..., ge=0, le=10)


class PresetRequest(BaseModel):
    preset: str = Field(..., regex=r"^[a-zA-Z_]+$")


class SignalRequest(BaseModel):
    type: str
    target_core: str
    symbol: str
    side: Optional[str] = None
    confidence: float = 0.0
    reason: Optional[str] = None
    correlation_id: Optional[str] = None
    timeframe: Optional[str] = None
    metadata: Dict[str, object] = Field(default_factory=dict)
    risk: Dict[str, object] = Field(default_factory=dict)


class CoreSnapshot(BaseModel):
    cores: Dict[str, CoreStatus]


class BackupRequest(BaseModel):
    trigger: Optional[str] = Field(default="auto")


class RecoveryRequest(BaseModel):
    issue_type: str = Field(default="auto")
    context: Dict[str, object] = Field(default_factory=dict)


class TokenProtected(BaseModel):
    token: Optional[str] = None


__all__ = [
    "CoreStatus",
    "ToggleRequest",
    "WeightRequest",
    "PresetRequest",
    "SignalRequest",
    "CoreSnapshot",
    "BackupRequest",
    "RecoveryRequest",
    "TokenProtected",
]
