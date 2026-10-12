# Operator runbook

## Profiles

| Profile | Use |
|---------|-----|
| `dev` | Local experiments, looser risk |
| `paper` | Default paper trading |
| `live` | Stricter risk knobs (still paper fills unless you wire a broker) |

```bash
set MP_PROFILE=paper
set MP_WEBHOOK_URL=https://discord.com/api/webhooks/...
set MP_LOG_LEVEL=INFO
```

## Backtest

```bash
money-printer backtest --strategy sma --symbol DEMO --csv data/sample_ohlcv.csv
money-printer backtest --strategy rsi --dry-run
```

Reports land in `reports/` as JSON + Markdown. Fills append to the profile journal SQLite DB.

## Kill switch

Create `data/STOP` (path from config) to block new entries. Remove the file to resume.

## Daemon

```bash
money-printer daemon --strategy sma --csv data/sample_ohlcv.csv --dry-run
```

Ctrl+C exits cleanly. Health is written to `data/health.json`.

## Risk knobs

- `max_position_pct` — fraction of equity per new buy  
- `max_open_positions` — concurrent symbols  
- `max_daily_loss_pct` — blocks new risk after drawdown from day start  
- `slippage_bps` / `commission_per_fill` — paper realism  
