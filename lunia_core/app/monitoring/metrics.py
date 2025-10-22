"""Prometheus metrics wrapper."""

from __future__ import annotations

import threading

from app.compat.prom import Counter, Gauge, Histogram, generate_latest


class MonitoringMetrics:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> "MonitoringMetrics":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_metrics()
        return cls._instance

    def _init_metrics(self) -> None:
        self.trades_executed = Counter("lunia_trades_executed_total", "Trades executed")
        self.core_pnl = Gauge("lunia_core_pnl", "PnL per core", ["core"])
        self.risk_exposure = Gauge("lunia_risk_exposure", "Risk exposure", ["core"])
        self.request_duration = Histogram(
            "lunia_request_duration_ms", "API duration ms"
        )
        self.llm_latency = Histogram(
            "lunia_llm_latency_ms", "LLM latency ms", ["provider"]
        )
        self.memory_usage = Gauge("lunia_memory_usage_mb", "Memory usage MB")
        self.cpu_usage = Gauge("lunia_cpu_usage_pct", "CPU usage percent")

    def export(self) -> bytes:
        return generate_latest()


MONITORING = MonitoringMetrics()
