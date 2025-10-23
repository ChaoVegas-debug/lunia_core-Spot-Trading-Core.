export const riskLimitsAdapter = (b: any) => ({
  drawdown: b?.max_dd_percent ?? b?.maxDrawdown,
  daily: b?.daily_loss_limit ?? b?.dailyLoss,
  leverage: b?.leverage_multiplier ?? b?.leverage,
});
