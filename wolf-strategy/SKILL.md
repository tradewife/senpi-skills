[SKILL (2).md](https://github.com/user-attachments/files/25500127/SKILL.2.md)
---
name: wolf-strategy
description: >-
  Fully autonomous 2-slot trading strategy for Hyperliquid perps.
  The WOLF hunts for its human — scans, enters, exits, and rotates
  positions without asking permission. IMMEDIATE_MOVER as primary entry
  trigger, mechanical DSL exits, concentration over diversification.
  7-cron architecture with race condition prevention. Scales to any
  budget ($500+). Proven: +$750 across 14 trades, 64% win rate.
  Use when running aggressive autonomous trading with concentrated
  positions, IMMEDIATE_MOVER entries, or 2-slot position management.
license: Apache-2.0
compatibility: >-
  Requires python3, mcporter, and cron. Depends on dsl-dynamic-stop-loss,
  opportunity-scanner, and emerging-movers skills.
metadata:
  author: jason-goldberg
  version: "3.1"
  platform: senpi
  exchange: hyperliquid
---

# WOLF v3.1 — Aggressive Autonomous Trading

The WOLF hunts for its human. It scans, enters, exits, and rotates positions autonomously — no permission needed. When criteria are met, the WOLF acts. Speed is edge.

2-slot concentrated position management. Mechanical exits, autonomous entries. DSL v4 handles all exit logic. The agent evaluates entry signals and acts immediately when the checklist passes. Scales to any budget from $500 to $50k+.

**Proven:** +$750 realized across 14 trades, 64% win rate in a single session ($6.5k budget).

## Autonomy Rules

**The WOLF operates autonomously by default.** The agent does NOT ask for permission to:
- Open a position when the entry checklist passes
- Close a position when DSL triggers, conviction collapses, or dead weight is detected
- Rotate out of a weak position into a stronger signal
- Cut losses when drawdown limits are hit

**The agent DOES notify the human** (via Telegram) after every action — entries, exits, rotations, and alerts. The human sees everything, but the WOLF doesn't wait.

**The only exception:** If the human explicitly tells the agent to require approval before trades (e.g., "ask me before entering positions"), the agent switches to confirmation mode. This must be an explicit request — the default is fully autonomous.

## Core Design

- **Fully autonomous** — scan, enter, exit, rotate without asking
- **2 slots max** — concentration beats diversification
- **Mechanical exits** via DSL v4 — no discretion on exits
- **IMMEDIATE_MOVER** is the primary entry trigger (not scanner score)
- **Aggressive rotation** — favor swapping into higher-conviction setups
- **Every slot must maximize ROI** — empty slot > mediocre position
- **Budget-scaled** — all sizing, limits, and stops derived from user's budget

## Budget-Scaled Parameters

All position sizing and risk limits are calculated from the user's budget. Nothing is hard-coded.

### Formulas

```
margin_per_slot    = budget × 0.30          (30% of budget per slot, 2 slots = 60% deployed max)
margin_buffer      = budget × 0.40          (40% reserve for margin health)
notional_per_slot  = margin_per_slot × leverage
daily_loss_limit   = budget × -0.15         (max 15% loss per day)
drawdown_cap       = budget × -0.30         (max 30% total drawdown → hard stop)
```

### Examples at Different Budgets

| Budget | Margin/Slot | Notional/Slot (10x) | Daily Loss Limit | Drawdown Cap |
|--------|-------------|---------------------|------------------|--------------|
| $500 | $150 | $1,500 | -$75 | -$150 |
| $1,000 | $300 | $3,000 | -$150 | -$300 |
| $2,000 | $600 | $6,000 | -$300 | -$600 |
| $4,000 | $1,200 | $12,000 | -$600 | -$1,200 |
| $6,500 | $1,950 | $19,500 | -$975 | -$1,950 |
| $10,000 | $3,000 | $30,000 | -$1,500 | -$3,000 |
| $25,000 | $7,500 | $75,000 | -$3,750 | -$7,500 |

### Why 30/30/40 Split

- **30% Slot A + 30% Slot B = 60% max deployed.** Concentration, not diversification.
- **40% margin buffer.** Cross-margin health degrades fast with 2 leveraged positions. At 10x with 2 positions, 40% buffer keeps margin ratio healthy even during drawdowns.
  - 2 positions at 60% deployed → ~89% margin buffer
  - If one position is losing 5% ROE, buffer is still ~84%
  - Buffer below 70% → the agent should cut the weaker position

### Minimum Budget

**$500.** At $150/slot margin with 10x leverage, you're trading $1,500 notional. This works on Hyperliquid but leaves tight margin — the agent should use conservative leverage (5-7x) at this budget.

| Budget | Recommended Leverage | Rationale |
|--------|---------------------|-----------|
| $500-$1k | 5-7x | Tight margin, need room for drawdown |
| $1k-$5k | 7-10x | Standard range, good margin buffer |
| $5k-$15k | 10-15x | Comfortable buffer, can be more aggressive |
| $15k+ | 10-20x | Scale notional, not just leverage |

### Configuration

When the agent sets up WOLF, it asks the user for budget and calculates everything:

```json
{
  "budget": 4000,
  "slots": 2,
  "marginPerSlot": 1200,
  "marginBuffer": 1600,
  "defaultLeverage": 10,
  "maxLeverage": 20,
  "notionalPerSlot": 12000,
  "dailyLossLimit": -600,
  "drawdownCap": -1200,
  "wallet": "0x...",
  "strategyId": "uuid"
}
```

The agent MUST calculate these from budget at setup — never use fixed dollar amounts.

## Cron Architecture

| # | Job | Interval | Script | Purpose |
|---|-----|----------|--------|---------|
| 1 | Emerging Movers | 60s | `emerging-movers.py` | Hunt IMMEDIATE_MOVER signals |
| 2 | Opportunity Scanner | 15min | `opportunity-scan.py` | Deep-dive scoring, threshold 175+ |
| 3 | DSL (per position) | 180s | `dsl-v4.py` | Trailing stops — created/destroyed per position |
| 4 | SM Flip Detector | 5min | (inline) | Conviction collapse detection |
| 5 | Watchdog | 5min | (inline) | Stale position detection |
| 6 | Portfolio Update | 15min | (agent heartbeat) | PnL reporting |
| 7 | Health Check | 10min | (inline) | Orphan DSL detection |

**DSL crons are ephemeral:** created when a position opens, destroyed when it closes.

**Race condition rule:** When ANY job closes a position → immediately deactivate DSL state file + disable DSL cron in the same action.

## Entry Rules

### Primary Signal: IMMEDIATE_MOVER

Emerging Movers fires IMMEDIATE_MOVER when an asset jumps 10+ ranks from #25+ in a single 60-second scan. **Act immediately** — don't wait for scanner confirmation, don't ask the human. If the checklist passes, enter the position.

**Entry checklist:**
1. IMMEDIATE_MOVER fired with `erratic: false` + `lowVelocity: false`
2. Hourly trend aligned (LONG needs hourlyTrend UP, SHORT needs DOWN)
3. SM conviction ≥ 2 and trader count ≥ 30
4. Max leverage ≥ 10x (check `max-leverage.json`)
5. Not already holding this asset
6. Slot available (max 2 positions)
7. Position size = `marginPerSlot` at configured leverage

### Secondary Signal: Opportunity Scanner (Score 175+)

Scanner runs every 15 min. Use for entries when no IMMEDIATE is firing.

### Position Sizing by Score

| Scanner Score | Size |
|---|---|
| 250+ | Full `marginPerSlot` |
| 200-250 | 75% of `marginPerSlot` |
| 175-200 | 50% of `marginPerSlot` |
| < 175 | Skip |

IMMEDIATE_MOVER entries always use full `marginPerSlot` — the signal is time-sensitive and already quality-filtered.

### What to Skip

- Erratic rank history (`erratic: true`)
- Low velocity (`lowVelocity: true`)
- < 10 SM traders
- Counter-trend on hourly
- Max leverage < 10x

## Exit Rules

See [references/exit-rules.md](references/exit-rules.md) for complete exit logic.

1. **DSL v4 Mechanical Exit** — primary. Handles all trailing stops automatically.
2. **SM Conviction Collapse** — conviction drops 4→1 (e.g., 220→24 traders) → cut immediately.
3. **Dead Weight Rule** — conviction 0, no SM interest → cut immediately.
4. **Race Condition Prevention** — when closing: deactivate DSL state + disable cron in same action.

## Rotation Rules

**The WOLF constantly evaluates whether each position deserves its slot.** Every scan cycle, every SM flip check, every cron tick — the agent asks: "Is this position still the best use of this slot, or would I be better off rotating into the new signal?" Dead weight is the enemy. A stagnant position that's going nowhere is costing you the opportunity to catch the next move.

**Rotate immediately if ANY of these are true:**
- New IMMEDIATE_MOVER firing while current position is flat or negative
- Current position in Phase 1 with no tier hit after 30+ minutes — it's not moving, cut it
- New opportunity scores 50+ points higher than current position's entry score
- Current position has SM conviction 0 or declining conviction — the smart money left
- Current position is negative and hourly trend has flipped against it

**Hold only if ALL of these are true:**
- Current position is in DSL Tier 2+ (profit is locked, let it run)
- Current position has strong and rising SM conviction
- No IMMEDIATE_MOVER is firing with better metrics

**The bias is toward action.** When in doubt between holding a mediocre position and rotating into a fresh signal, rotate. The WOLF's proven edge comes from catching fast moves early — a position that's been flat for 30+ minutes has already told you it's not the one.

## Position Management & DSL

### Margin Types
- **Cross-margin** for standard Hyperliquid assets
- **Isolated margin** (`leverageType: "ISOLATED"`) for XYZ DEX positions

### DSL Tier Structure

| Tier | Trigger ROE | Lock | Retrace |
|------|-------------|------|---------|
| 1 | 10% | 5% | 1.5% |
| 2 | 20% | 14% | 1.2% |
| 3 | 30% | 22% | 1.0% |
| 4 | 50% | 40% | 0.8% |
| 5 | 75% | 60% | 0.6% |
| 6 | 100% | 80% | 0.5% |

### Stagnation Take-Profit
Auto-close if ROE ≥ 8% and high-water stale for 1 hour.

## Proven Session Results

See [references/session-results.md](references/session-results.md) for the complete Feb 23, 2026 trade log.

**Summary:** 14 trades, 9 wins / 5 losses, 64% win rate, +$750 realized (on $6.5k budget).

## Key Learnings

See [references/learnings.md](references/learnings.md) for bugs, footguns, and trading discipline notes.

## Setup Checklist

1. Install companion skills: `dsl-dynamic-stop-loss`, `opportunity-scanner`, `emerging-movers`
2. Agent asks user for **budget** (minimum $500)
3. Agent calculates all parameters from budget (margin/slot, limits, leverage)
4. Create strategy wallet, fund with budget
5. Set up all 7 cron jobs
6. Create `max-leverage.json` reference file
7. Agent watches Emerging Movers for IMMEDIATE_MOVER signals and acts
