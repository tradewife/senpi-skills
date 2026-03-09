# 🐍 VIPER — Range-Bound Liquidity Sniper

The chop predator. Detects assets in tight ranges (low ATR, tight BBands, declining volume), enters at support/resistance with tight stops. Works when trending strategies are sitting idle.

## Architecture

| Script | Freq | Purpose |
|--------|------|---------|
| `viper-scanner.py` | 5 min | Scan 30 assets for range setups, BB/RSI/ATR analysis |
| DSL v5 (shared) | 3 min | Trailing stops |

## Edge

Range-bound markets are predictable: price bounces between support and resistance. Tight stops, high win rate, small gains per trade. The anti-momentum strategy.

## Setup

1. Set `VIPER_WALLET` and `VIPER_STRATEGY_ID` env vars (or fill `viper-config.json`)
2. Create cron: scanner every 5 min + DSL v5 every 3 min
