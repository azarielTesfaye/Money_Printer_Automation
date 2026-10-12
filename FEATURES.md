# Feature delivery plan (this repo)

Honest commits — date them when you actually push. Suggested commit slices:

1. `chore: scaffold pyproject, package layout, gitignore`
2. `feat(config): yaml profiles + dataclass settings`
3. `feat(data): MarketDataProvider + CSV replay`
4. `feat(data): optional Yahoo adapter with retry`
5. `feat(strategy): registry + SMA crossover`
6. `feat(strategy): RSI mean reversion`
7. `feat(portfolio): cash/positions ledger`
8. `feat(risk): kill switch, max loss, position caps`
9. `feat(execution): paper fills with slippage/commission`
10. `feat(journal): sqlite fills schema v1`
11. `feat(metrics): sharpe, drawdown, win rate`
12. `feat(engine): backtest runner + JSON/MD reports`
13. `feat(cli): backtest / daemon / strategies commands`
14. `feat(ops): health file + webhook notifier`
15. `test: sma/rsi/risk/e2e + CI workflow`
16. `docs: README + operator runbook`

## Status

All of the above are implemented under `src/money_printer/`. Run `pytest` and `money-printer backtest` to verify.
