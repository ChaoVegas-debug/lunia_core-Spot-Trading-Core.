"""Strategy adapters used in backtests."""

from .futures_adapter import FuturesStrategyAdapter
from .hft_adapter import HFTStrategyAdapter
from .spot_adapter import SpotStrategyAdapter

__all__ = ["SpotStrategyAdapter", "FuturesStrategyAdapter", "HFTStrategyAdapter"]
