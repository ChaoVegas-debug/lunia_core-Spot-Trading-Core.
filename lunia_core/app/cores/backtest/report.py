"""Report helpers for backtesting."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable


class BacktestReportGenerator:
    """Generates lightweight backtest reports."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path("logs/backtests")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, result, template: str = "default") -> str:
        path = (
            self.output_dir
            / f"{result.strategy.name}-{result.started_at:%Y%m%d%H%M%S}.html"
        )
        html = ["<html><body>", f"<h1>{result.strategy.name}</h1>"]
        html.append("<ul>")
        for key, value in result.metrics.items():
            html.append(f"<li>{key}: {value}</li>")
        html.append("</ul>")
        html.append("</body></html>")
        path.write_text("\n".join(html), encoding="utf-8")
        return str(path)

    def generate_metrics_summary(
        self, results: Iterable[Dict[str, float]]
    ) -> Dict[str, float]:
        summary: Dict[str, float] = {}
        count = 0
        for metrics in results:
            count += 1
            for key, value in metrics.items():
                summary[key] = summary.get(key, 0.0) + float(value)
        if count:
            for key in summary:
                summary[key] = summary[key] / count
        return summary

    def create_equity_curve_plot(self, equity_data: Iterable[float]) -> str:
        path = self.output_dir / "equity_curve.json"
        path.write_text(json.dumps(list(equity_data)), encoding="utf-8")
        return str(path)
