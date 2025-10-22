"""Risk insight agent used for portfolio explanations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from ...core.portfolio.portfolio import Portfolio, Position
from ...core.risk.manager import RiskManager
from ...core.utils import split_symbol


@dataclass
class RiskAssessment:
    score: float
    reason: str
    exposure_pct: float
    leverage: float
    compliant: bool


class RiskInsightAgent:
    """Compute risk related insights for a specific asset."""

    def __init__(self, risk_manager: RiskManager | None = None) -> None:
        self.risk_manager = risk_manager or RiskManager()

    def assess(
        self,
        asset: str,
        portfolio: Portfolio,
        *,
        equity: float,
        balances: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> RiskAssessment:
        asset = asset.upper()
        position: Optional[Position] = portfolio.get_position(asset)
        if position is None or position.quantity == 0:
            return RiskAssessment(
                score=0.55,
                reason="Нет открытой позиции — риск нейтрален",
                exposure_pct=0.0,
                leverage=0.0,
                compliant=True,
            )

        mark_price = portfolio.market_prices.get(asset, position.average_price)
        notional = abs(position.quantity) * mark_price
        equity_usd = max(equity, 1.0)
        leverage = notional / equity_usd if equity_usd else 0.0
        exposure_pct = (notional / equity_usd) * 100 if equity_usd else 0.0
        compliant, reason = self.risk_manager.validate_order(
            equity_usd=equity_usd,
            order_value_usd=notional,
            leverage=max(leverage, 1.0),
            symbol=asset,
            side="BUY" if position.quantity >= 0 else "SELL",
            abuse_context={"source": "risk_insight"},
        )

        score = 0.8 if compliant else 0.2
        reason_text = (
            "Риск-профиль в пределах лимитов"
            if compliant
            else f"Блокировано риск-менеджером: {reason}"
        )

        if balances:
            base_asset, _ = split_symbol(asset)
            asset_balance = balances.get(base_asset, {})
            free_balance = asset_balance.get("free", 0.0)
            if free_balance and notional:
                coverage = min(free_balance * mark_price / notional, 1.0)
                score = (score + coverage) / 2

        return RiskAssessment(
            score=max(0.0, min(score, 1.0)),
            reason=reason_text,
            exposure_pct=round(exposure_pct, 4),
            leverage=round(leverage, 4),
            compliant=compliant,
        )
