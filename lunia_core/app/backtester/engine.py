"""Lightweight backtesting primitives for the sandbox API."""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from statistics import mean, pstdev
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BacktestRequest:
    """Configuration submitted by the user."""

    strategy: str
    days: int
    initial_capital: float


@dataclass
class BacktestMetrics:
    """Aggregated statistics for a completed backtest."""

    total_return_pct: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown_pct: float
    average_slippage_bps: float
    average_latency_ms: float


@dataclass
class BacktestResult:
    """Detailed result produced by the engine."""

    request: BacktestRequest
    metrics: BacktestMetrics
    equity_curve: List[Dict[str, float]]
    trades: List[Dict[str, float]]
    completed_at: float


@dataclass
class BacktestJob:
    """Represents the lifecycle of a submitted backtest."""

    job_id: str
    request: BacktestRequest
    status: str = "queued"
    submitted_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result: Optional[BacktestResult] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "job_id": self.job_id,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "updated_at": self.updated_at,
            "request": {
                "strategy": self.request.strategy,
                "days": self.request.days,
                "initial_capital": self.request.initial_capital,
            },
        }
        if self.result:
            payload["result"] = {
                "metrics": self.result.metrics.__dict__,
                "equity_curve": self.result.equity_curve,
                "trades": self.result.trades,
                "completed_at": self.result.completed_at,
            }
        if self.error:
            payload["error"] = self.error
        return payload


class BacktestEngine:
    """Deterministic synthetic backtest implementation."""

    def run(self, request: BacktestRequest) -> BacktestResult:
        start = time.time()
        returns: List[float] = []
        equity_curve: List[Dict[str, float]] = []
        trades: List[Dict[str, float]] = []

        capital = request.initial_capital
        price = 100.0
        seed = abs(hash((request.strategy, request.days))) % 1_000_000
        # Deterministic pseudo random walk using sine + cosine variations.
        for day in range(1, request.days + 1):
            phase = (seed + day) / 50.0
            base_drift = math.sin(phase) * 0.006
            strategy_bias = {
                "conservative": 0.0008,
                "balanced": 0.0012,
                "aggressive": 0.002,
            }.get(request.strategy.lower(), 0.001)
            noise = math.cos(phase * 1.3) * 0.004
            daily_return = base_drift + strategy_bias + noise
            returns.append(daily_return)
            price *= 1 + daily_return
            capital *= 1 + daily_return
            equity_curve.append({"day": float(day), "equity": round(capital, 2)})

            if day % max(1, request.days // 6 or 1) == 0:
                trades.append(
                    {
                        "day": float(day),
                        "price": round(price, 2),
                        "pnl_pct": round(daily_return * 100, 3),
                    }
                )

        avg_return = mean(returns) if returns else 0.0
        volatility = pstdev(returns) if len(returns) > 1 else 0.0
        sharpe = (avg_return / volatility * math.sqrt(252)) if volatility else 0.0
        cumulative = (capital - request.initial_capital) / request.initial_capital * 100
        drawdown = self._max_drawdown(equity_curve, request.initial_capital)
        win_rate = sum(1 for r in returns if r > 0) / len(returns) if returns else 0.0
        latency_ms = 45.0 + (10.0 * math.sin(seed % 10))
        slippage_bps = 4.0 + (2.0 * math.cos(seed % 17))

        metrics = BacktestMetrics(
            total_return_pct=round(cumulative, 3),
            win_rate=round(win_rate * 100, 2),
            sharpe_ratio=round(sharpe, 3),
            max_drawdown_pct=round(drawdown, 3),
            average_slippage_bps=round(slippage_bps, 2),
            average_latency_ms=round(latency_ms, 2),
        )

        logger.info(
            "sandbox.backtest.completed strategy=%s days=%s total_return=%.3f sharpe=%.3f",
            request.strategy,
            request.days,
            metrics.total_return_pct,
            metrics.sharpe_ratio,
        )

        return BacktestResult(
            request=request,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            completed_at=time.time() - start,
        )

    @staticmethod
    def _max_drawdown(curve: List[Dict[str, float]], initial: float) -> float:
        peak = initial
        max_dd = 0.0
        for point in curve:
            equity = point["equity"]
            peak = max(peak, equity)
            if peak:
                drawdown = (equity - peak) / peak * 100
                max_dd = min(max_dd, drawdown)
        return abs(max_dd)


class BacktestJobManager:
    """In-memory job manager for sandbox backtests."""

    def __init__(self, engine: Optional[BacktestEngine] = None) -> None:
        self._engine = engine or BacktestEngine()
        self._jobs: Dict[str, BacktestJob] = {}
        self._lock = threading.Lock()

    def submit(self, request: BacktestRequest) -> BacktestJob:
        job_id = str(uuid.uuid4())
        job = BacktestJob(job_id=job_id, request=request)
        with self._lock:
            self._jobs[job_id] = job
        thread = threading.Thread(target=self._run_job, args=(job_id,), daemon=True)
        thread.start()
        return job

    def _run_job(self, job_id: str) -> None:
        job = self._jobs[job_id]
        job.status = "running"
        job.updated_at = time.time()
        try:
            result = self._engine.run(job.request)
            job.result = result
            job.status = "completed"
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("sandbox.backtest.failed job=%s error=%s", job_id, exc)
            job.error = str(exc)
            job.status = "failed"
        finally:
            job.updated_at = time.time()

    def get(self, job_id: str) -> Optional[BacktestJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def to_dict(self, job_id: str) -> Optional[Dict[str, object]]:
        job = self.get(job_id)
        return job.to_dict() if job else None
