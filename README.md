# Money Printer Automation

Paper-trading automation pipeline: market data → strategies → risk / sizing → broker fills → journal → analytics / reports.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
pytest -q --cov=money_printer --cov-report=term-missing
python -m money_printer backtest --strategy sma --symbol DEMO --csv data/sample_ohlcv.csv --analytics
```

## Strategies

`sma`, `rsi`, `macd`, `bollinger`, `momentum`, `atr_breakout`

## Brokers & sizing

- Paper broker (immediate fills) and simulated exchange (partials / rejects)
- Position sizers: fixed fractional, volatility target, ATR risk, fractional Kelly

## Walk-forward

```bash
python -m money_printer walkforward --strategy sma --train-bars 40 --test-bars 20
```

## Profiles

Set `MP_PROFILE` to `dev`, `paper`, or `live`. Secrets come from environment variables only.

See [docs/runbook.md](docs/runbook.md) for operator details.
