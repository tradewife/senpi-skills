---
name: wolf-strategy
description: >-
  Fully autonomous 2-3 slot trading strategy for Hyperliquid perps.
  The WOLF hunts for its human — scans, enters, exits, and rotates
  positions without asking permission. IMMEDIATE_MOVER as primary entry
  trigger, mechanical DSL exits, concentration over diversification.
  7-cron architecture with race condition prevention. Scales to any
  budget ($500+). Proven: +$1,500 across 20+ trades, 67% win rate.
  Use when running aggressive autonomous trading with concentrated
  positions, IMMEDIATE_MOVER entries, or 2-3 slot position management.
license: Apache-2.0
compatibility: >-
  Requires python3, mcporter, and cron. Depends on dsl-dynamic-stop-loss,
  opportunity-scanner, and emerging-movers skills.
metadata:
  author: jason-goldberg
  version: "4.0"
  platform: senpi
  exchange: hyperliquid
---

# WOLF v4.0 — Aggressive Autonomous Trading

The WOLF hunts for its human. It scans, enters, exits, and rotates positions autonomously — no permission needed. When criteria are met, the WOLF acts. Speed is edge.

2-3 slot concentrated position management. Mechanical exits, autonomous entries. DSL v4 handles all exit logic. The agent evaluates entry signals and acts immediately when the checklist passes. Scales to any budget from $500 to $50k+.

**Proven:** +$1,500 realized across 20+ trades, 67% win rate in a single session ($6.5k→$7k budget).

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
- **2-3 slots** — concentration beats diversification, scale slots with account size
- **Mechanical exits** via DSL v4 — no discretion on exits
- **IMMEDIATE_MOVER** is the primary entry trigger (not scanner score)
- **Aggressive rotation** — favor swapping into higher-conviction setups
- **Every slot must maximize ROI** — empty slot > mediocre position
- **Budget-scaled** — all sizing, limits, and stops derived from user's budget

## Slot Scaling & Auto-Delever

Slots scale with account size. The agent adjusts automatically:

| Account Value | Max Slots | Rationale |
|---------------|-----------|-----------|
| < $3,000 | 2 | Tight margin, need buffer |
| $3,000-$6,000 | 2 | Standard operation |
| $6,000-$10,000 | 3 | Enough buffer for 3 positions |
| $10,000+ | 3 | Comfortable, could extend to 4 |

**Auto-Delever Rule:** If account drops below the 3-slot threshold (e.g., $6,000), immediately revert to max 2 positions and close the weakest if 3 are open. This prevents margin death spirals.

## Budget-Scaled Parameters

All position sizing and risk limits are calculated from the user's budget. Nothing is hard-coded.

### Formulas

```
margin_per_slot    = budget × 0.30          (30% of budget per slot)
margin_buffer      = budget × (1 - 0.30 × slots)  (remaining after all slots)
notional_per_slot  = margin_per_slot × leverage
daily_loss_limit   = budget × -0.15         (max 15% loss per day)
drawdown_cap       = budget × -0.30         (max 30% total drawdown → hard stop)
```

### Examples at Different Budgets

| Budget | Slots | Margin/Slot | Notional (10x) | Daily Loss Limit | Drawdown Cap |
|--------|-------|-------------|----------------|------------------|--------------|
| $500 | 2 | $150 | $1,500 | -$75 | -$150 |
| $1,000 | 2 | $300 | $3,000 | -$150 | -$300 |
| $2,000 | 2 | $600 | $6,000 | -$300 | -$600 |
| $4,000 | 2 | $1,200 | $12,000 | -$600 | -$1,200 |
| $6,500 | 3 | $1,950 | $19,500 | -$975 | -$1,950 |
| $10,000 | 3 | $3,000 | $30,000 | -$1,500 | -$3,000 |
| $25,000 | 3 | $7,500 | $75,000 | -$3,750 | -$7,500 |

### Why 30% Per Slot

- **2 slots = 60% deployed, 40% buffer.** Buffer keeps cross-margin healthy.
- **3 slots = 90% deployed, 10% buffer.** Tighter — agent must watch buffer and cut weakest if it drops below 30%.
- Buffer below 50% → WARNING. Buffer below 30% → CRITICAL, cut weakest.

### Minimum Budget

**$500.** At $150/slot margin with 10x leverage, you're trading $1,500 notional. This works on Hyperliquid but leaves tight margin — the agent should use conservative leverage (5-7x) at this budget.

| Budget | Recommended Leverage | Rationale |
|--------|---------------------|-----------|
| $500-$1k | 5-7x | Tight margin, need room for drawdown |
| $1k-$5k | 7-10x | Standard range, good margin buffer |
| $5k-$15k | 10x | Sweet spot — proven range |
| $15k+ | 10-20x | Scale notional, not just leverage |

### Configuration

When the agent sets up WOLF, it asks the user for budget and calculates everything:

```json
{
  "budget": 6500,
  "slots": 3,
  "marginPerSlot": 1950,
  "marginBuffer": 650,
  "defaultLeverage": 10,
  "maxLeverage": 20,
  "notionalPerSlot": 19500,
  "dailyLossLimit": -975,
  "drawdownCap": -1950,
  "autoDeleverThreshold": 6000,
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
| 4 | SM Flip Detector | 5min | `sm-flip-check.py` | Conviction collapse detection |
| 5 | Watchdog | 5min | `wolf-monitor.py` | Margin buffer + position health monitoring |
| 6 | Portfolio Update | 15min | (agent heartbeat) | PnL reporting |
| 7 | Health Check | 10min | `job-health-check.py` | Orphan DSL detection, stale cron alerts |

**DSL crons are ephemeral:** created when a position opens, destroyed when it closes.

**Race condition rule:** When ANY job closes a position → immediately deactivate DSL state file + disable DSL cron in the same action. Multiple cron jobs can race each other — scanner closes a position, then DSL fires 1-3 min later and finds it "already closed."

**Token optimization:** Skip redundant checks when data is <3 min old. If scanner just ran and found no IMMEDIATEs, skip the next 60s trigger. If 3/3 slots full and no IMMEDIATEs, skip the opportunity scanner entirely.

## Entry Rules

### Primary Signal: IMMEDIATE_MOVER

Emerging Movers fires IMMEDIATE_MOVER when an asset jumps 10+ ranks from #25+ in a single 60-second scan. **Act immediately** — don't wait for scanner confirmation, don't ask the human. If the checklist passes, enter the position.

**Entry checklist:**
1. IMMEDIATE_MOVER fired with `erratic: false` AND `lowVelocity: false`
2. Positive contribVelocity (≥ 0.03 for IMMEDIATE status)
3. ≥ 10 SM traders (for crypto assets; for XYZ equities, trader count is less important — focus on reason count and velocity)
4. Max leverage ≥ 10x (check `max-leverage.json` — real max, not scanner suggestion)
5. Not already holding this asset
6. Slot available
7. Position size = `marginPerSlot` at configured leverage

**What changed from v3.1:** Removed SM conviction gate (≥2) and lowered trader threshold from 30 to 10. We successfully entered APT (25 traders, conv 0), SNDK (14 traders), and multiple others that were winners. By the time conviction is 4, the move is priced in. Rank climb velocity IS the entry signal — conviction is lagging.

**XYZ equities special rule:** Ignore trader count for XYZ assets. These are new instruments and not everyone is trading them. Use reason count (3+) and rank climb velocity as entry signals.

### v4 Filters (Erratic Rank Detection)

- **Erratic**: >5 rank reversals in history = zigzag noise → downgrade from IMMEDIATE to DEEP_CLIMBER
- **Low velocity**: contribVelocity < 0.03 → downgrade from IMMEDIATE
- Both filters prevent entering noise signals that look like big moves

### Secondary Signal: Opportunity Scanner (Score 175+)

Scanner runs every 15 min. Use for entries when no IMMEDIATE is firing and slots are open.

### Oversold Decline Rule

**Skip short entries when RSI < 30 AND extended 24h move (> -4%).** Even high-scoring shorts (BTC 196, XRP 189, ZRO 189) should be declined when oversold — bounce risk eats leveraged shorts. This rule saved us from multiple losing entries in the Feb 23 session.

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
- < 10 SM traders (crypto) — XYZ equities exempt
- Negative contribVelocity
- Already-peaked signals (rank was higher, now declining)
- Oversold shorts (RSI < 30 + extended 24h move)
- Max leverage < 10x (check `max-leverage.json`, NOT scanner's leverage suggestion)

## Exit Rules

### 1. DSL v4 Mechanical Exit (Primary)

All trailing stop logic is handled by DSL v4. The agent does NOT override DSL decisions.

**Phase 1 (Pre-Tier 1):** Absolute floor at entry ± 5%/leverage. 3 consecutive breaches = close.

**Phase 2 (Tier 1+):** Trailing floor based on high-water mark and tier lock percentage. Consecutive breaches per tier = close.

### 2. Stagnation Take-Profit

Auto-close if ROE ≥ 8% AND high-water mark hasn't moved for 1 hour. The position captured its move — take the profit before it retraces. This is built into DSL v4.

### 3. SM Conviction Collapse

If SM conviction drops dramatically (e.g., 4→1, 220→24 traders in minutes) → cut immediately. Don't wait for DSL. The smart money left.

### 4. Dead Weight Rule

SM conviction 0 + no SM interest + negative ROE for 30+ min → cut immediately. Every minute holding dead weight = missed opportunity for the next runner.

### 5. SM Flip (Conviction 4+ Against Position)

If SM conviction reaches 4+ in the OPPOSITE direction with 100+ traders → cut the position. Don't flip — just close and free the slot for the next clean entry.

### 6. Race Condition Prevention

When closing by ANY method: deactivate DSL state file + disable DSL cron **in the same action**. This prevents a second cron job from trying to close an already-closed position.

## Rotation Rules

**The WOLF constantly evaluates whether each position deserves its slot.**

**Rotate immediately if ANY of these are true:**
- New IMMEDIATE_MOVER firing while current position is flat or negative ROE
- Current position in Phase 1 with no progress after 30+ minutes AND a new IMMEDIATE is available
- New opportunity scores 50+ points higher than current position's entry score
- Current position has SM conviction 0 with declining momentum
- Current position is negative and hourly trend has flipped against it

**Hold only if ALL of these are true:**
- Current position is in DSL Tier 2+ (profit is locked, let it run)
- Current position has strong or rising SM conviction
- No IMMEDIATE_MOVER is firing with better metrics (more reasons, bigger rank jump)

**The bias is toward action** — but with data. A position that's been flat for 30 min is stagnating, but SNDK was flat for 13 min then ripped to +19% ROE. Use stagnation timer (1hr at 8%+ ROE) for mechanical exits; use rotation rules for signal-vs-signal comparisons.

## Position Management & DSL

### Margin Types
- **Cross-margin** for standard Hyperliquid crypto assets
- **Isolated margin** (`leverageType: "ISOLATED"`) for XYZ DEX positions (equities, metals, indices)
- Any wallet can hold BOTH cross crypto AND isolated XYZ side by side — no need for separate wallets
- XYZ assets use `xyz:` prefix (e.g., `xyz:GOLD`, `xyz:TSLA`, `xyz:XYZ100`) and require `dex="xyz"` in clearinghouse queries

### DSL Tier Structure (Actual — v4)

These are the LIVE tiers that produced +$1,500 in the proven session:

| Tier | Trigger ROE | Lock % of HW | Consecutive Breaches to Close |
|------|-------------|--------------|-------------------------------|
| 1 | 5% | 50% | 3 |
| 2 | 10% | 65% | 2 |
| 3 | 15% | 75% | 2 |
| 4 | 20% | 85% | 1 |

**Phase 1** (before Tier 1): Absolute floor at entry ± (5% / leverage). E.g., for 10x SHORT at $100 entry, floor = $100.50. 3 consecutive breaches = close.

**Phase 2** (Tier 1+): Trailing floor = HW × (1 - retrace%). Each tier tightens the retrace. Lock % means: if HW produced $200 profit, Tier 1 locks $100 (50%), Tier 2 locks $130 (65%), etc.

**Why 4 tiers at 5/10/15/20%, not 6 tiers at 10/20/30/50/75/100%:**
- Tighter tiers lock profit earlier — SNDK hit Tier 3 (+15% ROE) and locked $237
- The 6-tier version lets winners retrace too much before locking anything
- Most trades don't reach 30%+ ROE — they capture 5-20% and retrace. The 4-tier system captures that range optimally
- At 10x leverage, 5% ROE = only 0.5% price move. Tier 1 fires fast on real moves

### Stagnation Take-Profit
Auto-close if ROE ≥ 8% and high-water stale for 1 hour. Built into DSL v4.

### DSL State File Schema

Each position gets a JSON state file (`dsl-state-WOLF-{ASSET}.json`):

```json
{
  "active": true,
  "asset": "APT",
  "direction": "SHORT",
  "entryPrice": 0.8167,
  "leverage": 10,
  "size": 24452.87,
  "wallet": "0x...",
  "dex": null,
  "highWaterPrice": 0.8085,
  "phase": 1,
  "currentTierIndex": 0,
  "tierFloorPrice": null,
  "currentBreachCount": 0,
  "floorPrice": 0.820783,
  "phase1": {
    "retraceThreshold": 5,
    "consecutiveBreachesRequired": 3,
    "absoluteFloor": 0.820783
  },
  "phase2": {
    "retraceFromHW": 3,
    "breachesRequired": 2
  },
  "tiers": [
    { "triggerPct": 5, "lockPct": 50, "breaches": 3 },
    { "triggerPct": 10, "lockPct": 65, "breaches": 2 },
    { "triggerPct": 15, "lockPct": 75, "breaches": 2 },
    { "triggerPct": 20, "lockPct": 85, "breaches": 1 }
  ],
  "stagnation": {
    "enabled": true,
    "thresholdHours": 1.0,
    "minROE": 8.0
  }
}
```

**Critical:** `absoluteFloor` is auto-calculated by the DSL script. LONG = entry × (1 - threshold/leverage), SHORT = entry × (1 + threshold/leverage). NEVER manually compute floors in state files.

**Critical:** State file uses `active: true` (boolean), NOT `"status": "active"`.

**Critical:** DSL script reads `DSL_STATE_FILE` env var ONLY — positional args silently ignored.

**Critical:** Use `triggerPct` (percentage, e.g. 5) NOT `threshold` (decimal, e.g. 0.05). And use `lockPct` (not `retracePct`) for tier lock percentage.

## Known Bugs & Footguns

1. **Senpi `create_position` with `dryRun:true` ACTUALLY EXECUTES** — do not use dryRun
2. **DSL transient API failures**: Clearinghouse queries can fail transiently. DSL v4 retries (deactivates at 10 consecutive failures). Don't panic on 1 failure — use `execution_get_open_position_details` to verify before manual intervention.
3. **Health check can't see XYZ positions**: `job-health-check.py` doesn't query `dex=xyz`, causing false ORPHAN_DSL warnings for XYZ assets. Known issue, fix pending.
4. **Multiple cron jobs can race**: Scanner/SM closes a position, DSL fires 1-3 min later and finds it gone. Always deactivate DSL + disable cron when ANY job closes a position.
5. **Max leverage varies per asset**: Scanner's `leverage` field is a conservative suggestion, NOT the actual max. Check `max-leverage.json` (fetched from Hyperliquid API). E.g., WLFI is only 5x max — can't do 10x.
6. **`close_position` is the tool to close positions** (not `edit_position` with action=close)
7. **XYZ positions**: Use `leverageType: "ISOLATED"` in `create_position`. The WALLET isn't cross/isolated — individual POSITIONS are.

## Proven Session Results (Feb 23, 2026)

**20+ trades, 67% win rate, +$1,500 realized on $6.5k→$7k budget.**

Top winners:
- HYPE SHORT: +$560 (Tier 1→4, +15.5% ROE, let DSL run)
- XRP SHORT #1: +$303 (Tier 3 in 19 min)
- ETH SHORT #2: +$274 (Tier 1→4, ~18% ROE)
- SNDK SHORT: +$237 locked (Tier 3, +19% peak ROE in 65 min)
- LIT SHORT: +$205
- APT SHORT: +$178 (stagnation close at +9.3% ROE)

Key losses:
- NVDA LONG: -$114 (3/3 Phase 1 breaches, counter-trend)
- SILVER SHORT: -$72
- MON SHORT: -$62 (too few traders)
- MU SHORT: -$58 (dead weight, conv 0)

**Pattern:** Winners move FAST. XRP Tier 3 in 19 min, XMR Tier 2 in 37 min, SNDK +19% ROE in 45 min. If not moving within 30 min, probably won't. Speed of initial move is a quality signal.

## Key Learnings

- **Rank climb IS the entry signal — conviction is lagging**: Don't gate entries on conviction ≥4. By the time conviction is 4, the move is priced in.
- **Catch movers at #50→#35→#20**: Find big movers climbing from deep positions before they reach top 15.
- **PnL/contribution acceleration > trader count**: A fast-accelerating asset at rank #30 with 15 traders beats a stale rank #10 with 100 traders.
- **Conviction collapse = instant cut**: ETH went conv 4→1 (220→24 traders) in 10 min. Cut for -$12 instead of -$100+.
- **Don't anchor on past positions**: Evaluate every signal fresh. Past losses shouldn't make you gun-shy on the same asset.
- **Concentrate, don't spread thin**: 6 positions averaging -6% = slow death. 2-3 high-conviction positions is the way.
- **Hourly trend > SM signals**: SM conviction 4 on a 1-min bounce doesn't override a 2-week downtrend. NEVER go counter-trend on hourly.
- **Tier 1 lock doesn't guarantee profit**: SILVER hit Tier 1 then retraced through floor below entry. Tier locks protect from HW, but if price dumps below entry, you still lose.

## Setup Checklist

1. Install companion skills: `dsl-dynamic-stop-loss`, `opportunity-scanner`, `emerging-movers`
2. Agent asks user for **budget** (minimum $500)
3. Agent calculates all parameters from budget (margin/slot, slots, limits, leverage)
4. Create custom strategy wallet (`strategy_create_custom_strategy`), fund with budget
5. Set up all 7 cron jobs (DSL crons created per-position, not at setup)
6. Create `max-leverage.json` reference file (fetch from Hyperliquid `meta` API)
7. Agent watches Emerging Movers for IMMEDIATE_MOVER signals and acts
8. Set up quiet hours if user has a sleep schedule (batch updates, critical alerts only)
