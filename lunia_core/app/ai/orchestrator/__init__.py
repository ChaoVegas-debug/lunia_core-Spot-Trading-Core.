"""High level orchestrator that fuses agent insights."""

from __future__ import annotations

from .orchestrator import AgentOrchestrator

AGENT_ORCHESTRATOR = AgentOrchestrator()

__all__ = ["AGENT_ORCHESTRATOR", "AgentOrchestrator"]
