---
name: wolf-strategy
description: >-
  Fully autonomous aggressive trading strategy for Hyperliquid perps via Senpi MCP.
  7-cron architecture with Emerging Movers scanner (60s IMMEDIATE_MOVER signals),
  DSL v4 trailing stops (180s per position, 4-tier at 5/10/15/20% ROE),
  SM flip detector (5min), watchdog (5min), portfolio updates (15min),
  opportunity scanner (15min), and health checks (10min).
  Handles entries, exits, rotation, and race condition prevention fully autonomously.
  Use when setting up autonomous trading, managing leveraged positions with DSL,
  running the WOLF strategy, or hunting IMMEDIATE_MOVER signals on Hyperliquid.
  Requires Senpi MCP connection, python3, mcporter CLI, and OpenClaw cron system.
  Proven +$1,500 across 25+ trades at 65% win rate on $6.5k budget.
---

# WOLF v4 — Autonomous Trading Strategy

The WOLF hunts for its human. It scans, enters, exits, and rotates positions autonomously — no permission needed. When criteria are met, it acts. Speed is edge.

**Proven:** +$2,100 realized in first 24h, 25+ trades, 65% win rate, single session on $6.5k budget.

## Quick Start

1. Ensure Senpi MCP is connected (`mcporter list` should show `senpi`)
2. Create a custom strategy wallet: use `strategy_create_custom_strategy` via mcporter
3. Fund the wallet via `strategy_top_up` with your budget
4. Run setup: `python3 scripts/wolf-setup.py --wallet {WALLET} --strategy-id {STRATEGY_ID} --chat-id {CHAT_ID} --budget {BUDGET}` — the agent already knows wallet, strategy ID, and chat ID. It only needs to ask the user for their **budget**.
5. Create the 7 OpenClaw crons using templates from `references/cron-templates.md`
6. The WOLF is hunting

## Architecture — 7 Cron Jobs

| # | Job | Interval | Purpose |
|---|-----|----------|---------|
| 1 | Emerging Movers | 60s | Hunt IMMEDIATE_MOVER signals — primary entry trigger |
| 2 | DSL (per position) | 180s | Trailing stop exits — created/destroyed per position |
| 3 | SM Flip Detector | 5min | Cut positions where SM conviction collapses |
| 4 | Watchdog | 5min | Cross-margin buffer, liq distances, rotation candidates |
| 5 | Portfolio Update | 15min | PnL reporting to user |
| 6 | Opportunity Scanner | 15min | Deep-dive 4-pillar scoring, threshold 175+ |
| 7 | Health Check | 10min | Orphan DSL detection, stale cron alerts |

**DSL crons are ephemeral:** created when a position opens, destroyed when it closes.

## Cron Setup

**Critical:** Crons are **OpenClaw systemEvent crons**, NOT senpi crons. Each cron fires a systemEvent that wakes the agent with a MANDATE — explicit instructions telling the agent what to run and how to act on the output.

Create each cron using the OpenClaw cron tool:

```
cron add job={
  "name": "WOLF Emerging Movers (60s)",
  "schedule": { "kind": "every", "everyMs": 60000 },
  "sessionTarget": "main",
  "wakeMode": "now",
  "payload": { "kind": "systemEvent", "text": "<MANDATE TEXT>" }
}
```

The exact mandate text for each cron (with placeholders for wallet, budget, etc.) is in **`references/cron-templates.md`**. Read that file, replace the placeholders with your config values, and create all 7 crons.

**The mandate text is the secret sauce.** Without it, the agent just runs a script and stares at the output. The mandate tells the agent: "If IMMEDIATE_MOVER fires → OPEN position, set up DSL, alert user."

## Autonomy Rules

The WOLF operates autonomously by default. The agent does NOT ask permission to:
- Open a position when entry checklist passes
- Close a position when DSL triggers or conviction collapses
- Rotate out of weak positions into stronger signals
- Cut dead weight (SM conv 0, negative ROE, 30+ min)

The agent DOES notify the user (via Telegram) after every action.

## Entry Rules

### Primary: IMMEDIATE_MOVER (Emerging Movers Scanner)

Fires when an asset jumps 10+ ranks from #25+ in one 60-second scan.

**Checklist (all must pass):**
- `erratic: false` AND `lowVelocity: false`
- Positive contribVelocity (≥ 0.03)
- ≥ 10 SM traders (crypto); for XYZ equities, ignore trader count
- 4+ reasons for entry
- Max leverage ≥ 10x (check `max-leverage.json`, NOT scanner suggestion)
- Clean rank history (no zigzag)
- Slot available (or rotation justified)

### Secondary: Opportunity Scanner (Score 175+)

Runs every 15min. 3-stage funnel across all Hyperliquid perps. Score ≥ 175 with 0 risk flags.

### What to Skip

Negative velocity, erratic rank history, already-peaked, < 4 reasons, oversold shorts (RSI < 30 + extended 24h move).

## Exit Rules

1. **DSL v4 Mechanical Exit** — all trailing stops handled automatically
2. **SM Conviction Collapse** — conv drops to 0 or 4→1 with mass trader exodus → instant cut
3. **Dead Weight** — conv 0, negative ROE, 30+ min → instant cut
4. **SM Flip** — conviction 4+ opposite direction with 100+ traders → cut
5. **Race Condition Prevention** — when ANY job closes a position → immediately deactivate DSL state file + disable DSL cron in same action

## DSL v4 — Trailing Stop System

### Phase 1 (Pre-Tier 1): Absolute floor
- LONG floor = entry × (1 - 5%/leverage)
- SHORT floor = entry × (1 + 5%/leverage)
- 3 consecutive breaches → close

### Phase 2 (Tier 1+): Trailing tiers

| Tier | ROE Trigger | Lock % of HW | Breaches |
|------|-------------|--------------|----------|
| 1 | 5% | 50% | 2 |
| 2 | 10% | 65% | 2 |
| 3 | 15% | 75% | 2 |
| 4 | 20% | 85% | 1 |

**These are the LIVE tiers.** The old 6-tier version (10/20/30/50/75/100%) lets winners retrace too much.

### Stagnation Take-Profit
Auto-close if ROE ≥ 8% and high-water stale for 1 hour.

### DSL State File
Each position gets `dsl-state-WOLF-{ASSET}.json`. See `references/state-schema.md` for the full schema and critical gotchas (triggerPct not threshold, lockPct not retracePct, etc.).

## Rotation Rules

When slots are full and a new IMMEDIATE fires:
- **Rotate if:** new signal has 4+ reasons + positive velocity AND weakest position is flat/negative ROE with SM conv 0-1
- **Hold if:** current position in Tier 2+ or trending up with SM conv 3+

## Budget Scaling

All sizing is calculated from budget (30% per slot):

| Budget | Slots | Margin/Slot | Leverage | Daily Loss Limit |
|--------|-------|-------------|----------|------------------|
| $500 | 2 | $150 | 5-7x | -$75 |
| $2,000 | 2 | $600 | 10x | -$300 |
| $6,500 | 3 | $1,950 | 10x | -$975 |
| $10,000+ | 3-4 | $3,000 | 10x | -$1,500 |

**Auto-Delever:** If account drops below threshold → reduce max slots by 1, close weakest.

## Position Lifecycle

### Opening
1. Signal fires → validate checklist → `create_position` (use `leverageType: "ISOLATED"` for XYZ assets)
2. Create DSL state file (`dsl-state-WOLF-{ASSET}.json`) — see `references/state-schema.md`
3. Create DSL cron (180s) using template from `references/cron-templates.md`
4. Alert user

### Closing
1. Close via `close_position` (or DSL auto-closes)
2. **Immediately** set DSL state `active: false`
3. **Immediately** disable DSL cron
4. Alert user
5. Evaluate: empty slot or new signal?

## Margin Types
- **Cross-margin** for crypto (BTC, ETH, SOL, etc.)
- **Isolated margin** for XYZ DEX (GOLD, SILVER, TSLA, etc.) — set `leverageType: "ISOLATED"` and `dex: "xyz"`
- Same wallet holds both cross crypto + isolated XYZ side by side

## Token Optimization
- Skip redundant checks when data < 3 min old
- If all slots full and no IMMEDIATEs → skip scanner
- If SM check shows no flips and < 5 min old → skip

## Troubleshooting

See `references/learnings.md` for known bugs, gotchas, and trading discipline rules. Key ones:
- **`dryRun: true` actually executes** — NEVER use dryRun
- **DSL reads `DSL_STATE_FILE` env var ONLY** — positional args silently ignored
- **Max leverage varies per asset** — always check `max-leverage.json`
- **`close_position` is the close tool** — not `edit_position`
- **Tier 1 lock ≠ guaranteed profit** — lock is from HW, not entry

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/wolf-setup.py` | Setup wizard — creates config from budget |
| `scripts/emerging-movers.py` | Emerging Movers v3.1 scanner |
| `scripts/dsl-v4.py` | DSL v4 trailing stop engine |
| `scripts/sm-flip-check.py` | SM conviction flip detector |
| `scripts/wolf-monitor.py` | Watchdog — margin buffer + position health |
| `scripts/opportunity-scan.py` | Opportunity Scanner v5 |
| `scripts/job-health-check.py` | Orphan DSL / stale cron detector |
