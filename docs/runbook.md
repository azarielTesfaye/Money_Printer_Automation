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
python -m money_printer backtest --strategy sma --symbol DEMO --csv data/sample_ohlcv.csv
python -m money_printer backtest --strategy macd --analytics
python -m money_printer backtest --strategy momentum --sizer vol --sizer-param target_vol=0.12
python -m money_printer backtest --strategy rsi --dry-run
```

Reports land in `reports/` as JSON + Markdown. With `--analytics`, reports include Sortino, Calmar, underwater stats, monthly returns, and trade attribution.

## Walk-forward

```bash
python -m money_printer walkforward --strategy bollinger --train-bars 40 --test-bars 20 --step-bars 20
```

## Kill switch

Create `data/STOP` (path from config) to block new entries. Remove the file to resume.

## Daemon

```bash
python -m money_printer daemon --strategy sma --csv data/sample_ohlcv.csv --dry-run
```

Ctrl+C exits cleanly. Health is written to `data/health.json`.

## Risk & sizing knobs

- `max_position_pct` — default fixed-fraction budget when no custom sizer is passed  
- `max_open_positions` — concurrent symbols  
- `max_daily_loss_pct` — blocks new risk after drawdown from day start  
- `slippage_bps` / `commission_per_fill` — paper realism  
- CLI `--sizer fixed|vol|atr|kelly` with `--sizer-param key=value`

## OMS / storage / API

```bash
python -m money_printer migrate --db data/app_store.db
python -m money_printer serve --broker paper --port 8000
```

- OMS validates and routes orders through broker adapters without changing `BacktestEngine`
- Storage migrations are SQLite and additive
- Alpaca/Binance adapters default to `offline=True` (local paper/sim fills)

## Coverage

```bash
pytest -q --cov=money_printer --cov-report=term-missing
```
