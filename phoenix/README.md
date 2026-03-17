# 🔥 PHOENIX v1.0 — Contribution Velocity Scanner

Part of the [Senpi Trading Skills Zoo](https://github.com/Senpi-ai/senpi-skills).

## What PHOENIX Does

PHOENIX reads one field that no other scanner uses: `contribution_pct_change_4h` from `leaderboard_get_markets`.

This field measures how fast an asset's share of top trader profits is growing. When BTC's contribution is +32% over 4 hours but price only moved +0.7%, smart money is making leveraged gains on a tiny price move. More SM enters → more buying pressure → price catches up. The contribution velocity IS the leading indicator.

One API call. No scan history. No local state. The simplest scanner in the zoo.

## Why This Field Matters

Orca watches rank climbing over 3+ scans to detect SM interest building. But rank is a lagging indicator — it reflects relative position after contribution has already changed. The contribution velocity tells you SM interest is ACCELERATING before the rank moves.

From the March 17 snapshot:
```
BTC:  contribution 29.55%  │  change_4h +32.19%  │  price +0.70%  → 46x divergence
HYPE: contribution 15.86%  │  change_4h +19.12%  │  price -1.01%  → SM profiting on shorts
LIT:  contribution 10.73%  │  change_4h +10.68%  │  price +10.63% → SM riding the move
```

## Directory Structure

```
phoenix-v1.0/
├── README.md
├── SKILL.md
├── config/
│   └── phoenix-config.json
└── scripts/
    ├── phoenix-scanner.py
    └── phoenix_config.py
```

## Quick Start

1. Deploy `config/phoenix-config.json` with your wallet and strategy ID
2. Deploy `scripts/phoenix-scanner.py` and `scripts/phoenix_config.py`
3. Create scanner cron (90s, main session) and DSL cron (3 min, isolated)
4. Fund with $1,000 on the Senpi Predators leaderboard

## The Key Signal: Velocity vs Price Divergence

When `contribution_pct_change_4h` is 10x+ the actual price change, SM is profiting far more than the market has moved. This divergence is the alpha window — it closes when price catches up. PHOENIX scores this divergence directly (+2 points for 10x+, +1 for 5x+).

## Requires

- dsl-v5.py with Patch 1 (dynamic absoluteFloorRoe calculator) and Patch 2 (highWaterPrice null handling)
- Senpi MCP with `leaderboard_get_markets`

## License

MIT — Built by Senpi (https://senpi.ai).
Source: https://github.com/Senpi-ai/senpi-skills

## Changelog

### v1.0
- Initial release — contribution velocity scanner using `contribution_pct_change_4h`
- Velocity vs price divergence scoring (10x+ = high conviction)
- Single API call per scan, no local state, no scan history
- DSL v1.1.1 pattern: `highWaterPrice: null`, correct field names, dynamic `absoluteFloorRoe`
- 90-minute per-asset cooldown, XYZ equity ban, leverage floor 5x
