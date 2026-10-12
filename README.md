# Money Printer Automation

Paper-trading automation pipeline: market data → strategies → risk checks → fills → journal → reports.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
pytest
money-printer backtest --strategy sma --symbol DEMO --csv data/sample_ohlcv.csv
```

## Profiles

Set `MP_PROFILE` to `dev`, `paper`, or `live`. Secrets (webhook URLs, API keys) come from environment variables only.

See [docs/runbook.md](docs/runbook.md) for operator details.
