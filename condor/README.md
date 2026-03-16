# 🦅 CONDOR v1.0 — Multi-Asset Alpha Hunter

Part of the [Senpi Trading Skills](https://github.com/Senpi-ai/senpi-skills).

## What CONDOR Does

Grizzly's three-mode lifecycle across BTC, ETH, SOL, and HYPE. Evaluates all four every 3 minutes, commits to the single strongest thesis. One position at a time.

The single-asset hunters (Polar, Wolverine, Grizzly) sit idle when their asset isn't moving. Condor is always in the best trade available.

## How It Works

```
Every 3 min: Score BTC, ETH, SOL, HYPE
                    |
            Pick highest score (10+ required)
                    |
            HUNT → RIDE → STALK → RELOAD or RESET
                    |
            On thesis death: evaluate ALL 4 again
```

## Quick Start

1. Deploy config and scripts
2. Create scanner cron (3 min, main) and DSL cron (3 min, isolated)
3. Fund with $1,000

## License

MIT — see root repo LICENSE.
