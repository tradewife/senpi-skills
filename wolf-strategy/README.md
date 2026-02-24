# WOLF Strategy v4.0

Fully autonomous trading strategy for Hyperliquid perps. The WOLF hunts for its human — scans, enters, exits, and rotates positions without asking permission.

**Proven:** +$2,000 realized in 24h, 25+ trades, 65% win rate on $6.5k budget.

## What's Included

This is a complete, self-contained skill with all scripts bundled:

| File | Purpose |
|------|---------|
| `SKILL.md` | Strategy instructions, rules, and architecture |
| `scripts/wolf-setup.py` | **Setup wizard** — agent passes wallet/strategy/chat ID, only asks user for **budget** |
| `scripts/emerging-movers.py` | Emerging Movers v3.1 — primary entry signal (60s scans) |
| `scripts/dsl-v4.py` | DSL v4 trailing stop engine (4-tier at 5/10/15/20% ROE) |
| `scripts/opportunity-scan.py` | Opportunity Scanner v5 — 3-stage funnel, 4-pillar scoring |
| `scripts/sm-flip-check.py` | SM conviction flip detector |
| `scripts/wolf-monitor.py` | Watchdog — margin buffer + position health |
| `scripts/job-health-check.py` | Orphan DSL / stale cron detector |
| `references/cron-templates.md` | Exact cron MANDATE templates that make the agent ACT |
| `references/state-schema.md` | DSL state file + strategy config schemas with all gotchas |
| `references/learnings.md` | Proven results, known bugs, trading discipline rules |

## What's New in v4

- **All 7 Python scripts bundled** — no separate skill dependencies needed
- **Setup wizard** (`wolf-setup.py`) — asks budget, wallet, strategy ID, Telegram chat ID → calculates everything
- **Cron MANDATE templates** — the exact systemEvent payloads that make the agent act autonomously, not just report
- **Correct OpenClaw cron format** — systemEvent crons, not the broken `senpi.cron_create`
- **Tighter DSL tiers** — 4 tiers at 5/10/15/20% ROE (locks profit earlier than old 6-tier)
- **Entry filters fixed** — 10+ traders (not 30+), conviction gate removed (rank climb is the signal)
- **XYZ equities support** — isolated margin, `xyz:` prefix, trader count exempt
- **Oversold decline rule** — skip shorts when RSI < 30 + extended 24h move
- **Auto-delever** — scales slots down if account value drops below threshold
- **Token optimization** — skips redundant checks when data < 3 min old

## Quick Start

1. Download all files (or clone this folder)
2. Send `SKILL.md` to your Senpi agent: **"Here are some new superpowers"**
3. Tell the agent your **budget** — it handles everything else

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.0 | 2026-02-24 | Complete rewrite — all scripts bundled, setup wizard, cron mandates, tighter DSL tiers, entry filters fixed |
| v3.1 | 2026-02-23 | Budget-scaled parameters, autonomy rules, aggressive rotation |
| v3.0 | 2026-02-23 | Initial release. 2-slot, IMMEDIATE_MOVER entries, +$750 proven |
