[SKILL.md](https://github.com/user-attachments/files/25528015/SKILL.md)
---
name: wolf-strategy
description: >-
  WOLF v5 — Fully autonomous aggressive trading strategy for Hyperliquid perps via Senpi MCP.
  7-cron architecture with Emerging Movers scanner (90s, FIRST_JUMP + IMMEDIATE_MOVER signals),
  DSL v4 trailing stops (combined runner every 3min, 4-tier at 5/10/15/20% ROE),
  SM flip detector (5min), watchdog (5min), portfolio updates (15min),
  opportunity scanner (15min, broken/optional), and health checks (10min).
  Handles entries, exits, rotation, and race condition prevention fully autonomously.
  Minimum 7x leverage required. Enter early on first jumps, not at confirmed peaks.
  Requires Senpi MCP connection, python3, mcporter CLI, and OpenClaw cron system.
  Proven +$1,500 across 25+ trades at 65% win rate on $6.5k budget.
---

# WOLF v5 — Autonomous Trading Strategy

The WOLF hunts for its human. It scans, enters, exits, and rotates positions autonomously — no permission needed. When criteria are met, it acts. Speed is edge.

**Proven:** +$1,500 realized, 25+ trades, 65% win rate, single session on $6.5k budget.

---

## Entry Philosophy — THE Most Important Section

**Enter before the peak, not at the top.**

Leaderboard rank confirmation LAGS price. When an asset jumps from #31→#16 in one scan, the price is moving NOW. By the time it reaches #7 with clean history, the move is over. Speed is edge.

The old approach (wait for 4+ reasons, clean rank history, vel ≥ 0.03) filters out the BEST entries. An asset bouncing around #30-40 then jumping to #16 will always look "erratic" — but that's the entry signal, not noise.

**Core principle:** 2 reasons at rank #25 with a big jump = ENTER. 4+ reasons at rank #5 = SKIP (already peaked).

---

## Quick Start

1. Ensure Senpi MCP is connected (`mcporter list` should show `senpi`)
2. Create a custom strategy wallet: use `strategy_create_custom_strategy` via mcporter
3. Fund the wallet via `strategy_top_up` with your budget
4. Run setup: `python3 scripts/wolf-setup.py` — it will ask for wallet, strategy ID, budget, Telegram chat ID
5. Create the 7 OpenClaw crons using templates from `references/cron-templates.md`
6. The WOLF is hunting

---

## Architecture — 7 Cron Jobs

| # | Job | Interval | Script | Purpose |
|---|-----|----------|--------|---------|
| 1 | Emerging Movers | **90s** | `scripts/emerging-movers.py` | Hunt FIRST_JUMP + IMMEDIATE_MOVER signals — primary entry trigger |
| 2 | DSL Combined | **3min** | `scripts/dsl-combined.py` | Trailing stop exits for ALL open positions (single runner) |
| 3 | SM Flip Detector | 5min | `scripts/sm-flip-check.py` | Cut positions where SM conviction collapses |
| 4 | Watchdog | 5min | `scripts/wolf-monitor.py` | Cross-margin buffer, liq distances, rotation candidates |
| 5 | Portfolio Update | 15min | (agent-driven) | PnL reporting to user |
| 6 | Opportunity Scanner | 15min | `scripts/opportunity-scan.py` | Deep-dive 4-pillar scoring, threshold 175+ **(broken, optional)** |
| 7 | Health Check | 10min | `scripts/job-health-check.py` | Orphan DSL detection, stale cron alerts |

**v5 change:** DSL uses a combined runner (`dsl-combined.py`) every 3min instead of per-position crons. No more ephemeral DSL cron creation/destruction — one cron iterates all active DSL state files.

**v5 change:** Scanner interval is 90s (was 60s) — reduces token burn without missing signals.

## Cron Setup

**Critical:** Crons are **OpenClaw systemEvent crons**, NOT senpi crons. Each cron fires a systemEvent that wakes the agent with a MANDATE — explicit instructions telling the agent what to run and how to act on the output.

Create each cron using the OpenClaw cron tool:

```
cron add job={
  "name": "WOLF Emerging Movers (90s)",
  "schedule": { "kind": "every", "everyMs": 90000 },
  "sessionTarget": "main",
  "wakeMode": "now",
  "payload": { "kind": "systemEvent", "text": "<MANDATE TEXT>" }
}
```

The exact mandate text for each cron (with placeholders for wallet, budget, etc.) is in **`references/cron-templates.md`**. Read that file, replace the placeholders with your config values, and create all 7 crons.

**The mandate text is the secret sauce.** Without it, the agent just runs a script and stares at the output. The mandate tells the agent: "If FIRST_JUMP fires → OPEN position immediately, set up DSL state, alert user."

---

## Autonomy Rules

The WOLF operates autonomously by default. The agent does NOT ask permission to:
- Open a position when entry checklist passes
- Close a position when DSL triggers or conviction collapses
- Rotate out of weak positions into stronger signals
- Cut dead weight (SM conv 0, negative ROE, 30+ min)

The agent DOES notify the user (via Telegram) after every action.

---

## Entry Signals — Priority Order

### 1. FIRST_JUMP ⚡ (Highest Priority)

**What:** Asset jumps 10+ ranks from #25+ in ONE scan AND was not in previous scan's top 50 (or was at rank ≥ #30).

**Action:** Enter IMMEDIATELY. This is the money signal. By next scan it's too late.

**Checklist:**
- `isFirstJump: true` in scanner output
- **2+ reasons is enough** (don't require 4+)
- **vel > 0 is sufficient** (velocity hasn't had time to build on a first jump)
- Max leverage ≥ 7x (check `max-leverage.json`)
- Slot available (or rotation justified)
- ≥ 10 SM traders (crypto); for XYZ equities, ignore trader count

**What to ignore:**
- Erratic rank history — the scanner excludes the current jump from erratic checks. Pre-jump bouncing at #30-40 is normal.
- Low velocity — first jumps haven't had time to build velocity.

**If CONTRIB_EXPLOSION accompanies it:** Double confirmation. Even stronger entry.

### 2. CONTRIB_EXPLOSION 💥

**What:** 3x+ contribution increase in one scan from asset at rank #20+.

**Action:** Enter even if rank history looks "erratic." The contrib spike IS the signal regardless of prior rank bouncing.

**Checklist:**
- `isContribExplosion: true` in scanner output
- Asset currently at rank #20+
- 2+ reasons
- vel > 0
- Max leverage ≥ 7x
- Slot available

**Never downgraded for erratic history.** Often accompanies FIRST_JUMP for double confirmation.

### 3. DEEP_CLIMBER 📈

**What:** Steady climb from #30+, positive velocity (≥ 0.03), 3+ reasons, clean rank history.

**Action:** Enter when it crosses into top 20. This is the "safe" entry for steady movers.

**Checklist:**
- `isDeepClimber: true`, `erratic: false`, `lowVelocity: false`
- contribVelocity ≥ 0.03
- 3+ reasons
- ≥ 10 SM traders (crypto)
- Max leverage ≥ 7x
- Slot available

**Requires more confirmation than FIRST_JUMP.** This catches the grinders, not the explosive movers.

### 4. NEW_ENTRY_DEEP 🆕

**What:** Appears in top 20 from nowhere (wasn't in top 50 last scan).

**Action:** Instant entry — something is happening.

**Checklist:**
- Scanner shows `NEW_ENTRY_DEEP` in reasons
- 2+ reasons
- Max leverage ≥ 7x
- Slot available

### 5. Opportunity Scanner (Score 175+)

Runs every 15min. 3-stage funnel across all Hyperliquid perps. Score ≥ 175 with 0 risk flags. **(Currently broken/optional — Emerging Movers is the primary entry source.)**

---

## Anti-Patterns — When NOT to Enter

- **NEVER enter assets already at #1-10.** That's the top, not the entry. Rank = what already happened.
- **NEVER wait for a signal to "clean up."** By the time rank history is smooth and velocity is high, the move is priced in.
- **4+ reasons at rank #5 = SKIP.** The asset already peaked. You'd be buying the top.
- **2 reasons at rank #25 with a big jump = ENTER.** The move is just starting.
- **Leaderboard rank ≠ future price direction.** Rank reflects past trader concentration. Price moves first, rank follows.
- **Negative velocity + no jump = skip.** Slow bleeders going nowhere.
- **Oversold shorts** (RSI < 30 + extended 24h move) = skip.

---

## Late Entry Anti-Pattern

This deserves its own section because it's the #1 way to lose money with WOLF.

**The pattern:** Scanner fires FIRST_JUMP for ASSET at #25→#14. You hesitate. Next scan it's #10. Next scan #7 with 5 reasons and clean history. NOW it looks "safe." You enter. It reverses from #5.

**The fix:** Enter on the FIRST signal or don't enter at all. If you missed it, wait for the next asset. There's always another FIRST_JUMP coming.

**Rule:** If an asset has been in the top 10 for 2+ scans already, it's too late. Move on.

---

## Phase 1 Auto-Cut

Positions that never gain momentum get cut automatically.

**Rules:**
- **90-minute maximum** in Phase 1 (pre-Tier 1 DSL). If ROE never hits 5% in 90 minutes, close.
- **Weak peak early cut:** If peak ROE was < 3% and ROE is now declining → close after 45 minutes. Don't wait 90.
- **Dead weight:** SM conviction = 0, negative ROE, position open 30+ minutes → instant cut regardless of phase.

**Why:** Phase 1 positions have no trailing stop protection. They're running on faith. If SM conviction doesn't materialize in 90 min, the thesis is wrong.

---

## Exit Rules

### 1. DSL v4 Mechanical Exit (Trailing Stops)

All trailing stops handled automatically by `dsl-combined.py`.

### 2. SM Conviction Collapse
Conv drops to 0 or 4→1 with mass trader exodus → instant cut.

### 3. Dead Weight
Conv 0, negative ROE, 30+ min → instant cut.

### 4. SM Flip
Conviction 4+ in the OPPOSITE direction with 100+ traders → cut immediately.

### 5. Race Condition Prevention
When ANY job closes a position → immediately:
1. Set DSL state `active: false` in the state file
2. Alert user
3. Evaluate: empty slot for next signal?

**v5 change:** Since DSL is now a combined runner, no need to destroy per-position crons. Just set `active: false` in the state file.

---

## DSL v4 — Trailing Stop System

### Phase 1 (Pre-Tier 1): Absolute floor
- LONG floor = entry × (1 - 5%/leverage)
- SHORT floor = entry × (1 + 5%/leverage)
- 3 consecutive breaches → close
- **Max duration: 90 minutes** (see Phase 1 Auto-Cut above)

### Phase 2 (Tier 1+): Trailing tiers

| Tier | ROE Trigger | Lock % of High-Water | Breaches to Close |
|------|-------------|---------------------|-------------------|
| 1 | 5% | 50% | 2 |
| 2 | 10% | 65% | 2 |
| 3 | 15% | 75% | 2 |
| 4 | 20% | 85% | 1 |

### Stagnation Take-Profit
Auto-close if ROE ≥ 8% and high-water stale for 1 hour.

### DSL State File
Each position gets `dsl-state-WOLF-{ASSET}.json`. The combined runner iterates all active state files. See `references/state-schema.md` for the full schema and critical gotchas (triggerPct not threshold, lockPct not retracePct, etc.).

---

## Rotation Rules

When slots are full and a new FIRST_JUMP or IMMEDIATE fires:
- **Rotate if:** new signal is FIRST_JUMP or has 3+ reasons + positive velocity AND weakest position is flat/negative ROE with SM conv 0-1
- **Hold if:** current position in Tier 2+ or trending up with SM conv 3+

---

## Budget Scaling

All sizing is calculated from budget (30% per slot):

| Budget | Slots | Margin/Slot | Leverage | Daily Loss Limit |
|--------|-------|-------------|----------|------------------|
| $500 | 2 | $150 | 7x | -$75 |
| $2,000 | 2 | $600 | 10x | -$300 |
| $6,500 | 3 | $1,950 | 10x | -$975 |
| $10,000+ | 3-4 | $3,000 | 10x | -$1,500 |

**Minimum leverage: 7x.** If max leverage for an asset is below 7x, skip it. Low leverage = low ROE = DSL tiers never trigger = dead position.

**Auto-Delever:** If account drops below threshold → reduce max slots by 1, close weakest.

---

## Position Lifecycle

### Opening
1. Signal fires → validate checklist → `create_position` (use `leverageType: "ISOLATED"` for XYZ assets)
2. Create DSL state file (`dsl-state-WOLF-{ASSET}.json`) — see `references/state-schema.md`
3. Alert user

### Closing
1. Close via `close_position` (or DSL auto-closes)
2. **Immediately** set DSL state `active: false`
3. Alert user
4. Evaluate: empty slot or new signal?

---

## Margin Types

- **Cross-margin** for crypto (BTC, ETH, SOL, etc.)
- **Isolated margin** for XYZ DEX (GOLD, SILVER, TSLA, etc.) — set `leverageType: "ISOLATED"` and `dex: "xyz"`
- Same wallet holds both cross crypto + isolated XYZ side by side

---

## XYZ Equities

XYZ DEX assets (GOLD, SILVER, TSLA, AAPL, etc.) behave differently:

- **Ignore trader count.** XYZ equities often have low SM trader counts — this doesn't invalidate the signal.
- **Use reason count + rank velocity** as primary quality filter instead.
- **Always use isolated margin** (`leverageType: "ISOLATED"`, `dex: "xyz"`).
- **Check max leverage** — many XYZ assets cap at 5x or 3x. If below 7x, skip.

---

## Token Optimization

- Skip redundant checks when data < 3 min old
- If all slots full and no FIRST_JUMPs → skip scanner processing
- If SM check shows no flips and < 5 min old → skip

---

## Known Limitations

- **Watchdog blind spot for XYZ isolated:** The watchdog monitors cross-margin buffer but can't see isolated position liquidation distances in the same way. XYZ positions rely on DSL for protection.
- **Health check only sees crypto wallet:** The health check script checks wallet balance but doesn't account for margin locked in isolated XYZ positions. Total equity may differ from reported balance.
- **Opportunity Scanner is broken:** The 4-pillar scoring system (`scripts/opportunity-scan.py`) has reliability issues. Emerging Movers is the primary and proven entry source. The opportunity scanner cron is optional.
- **Scanner needs history:** The scanner requires ≥ 2 scans in history before it can generate alerts. First 2 scans after a fresh start produce no signals.

---

## Troubleshooting

See `references/learnings.md` for known bugs, gotchas, and trading discipline rules. Key ones:
- **`dryRun: true` actually executes** — NEVER use dryRun
- **DSL reads `DSL_STATE_FILE` env var ONLY** — positional args silently ignored
- **Max leverage varies per asset** — always check `max-leverage.json`
- **`close_position` is the close tool** — not `edit_position`
- **Tier 1 lock ≠ guaranteed profit** — lock is from high-water, not entry

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/wolf-setup.py` | Setup wizard — creates config from budget |
| `scripts/emerging-movers.py` | Emerging Movers v4 scanner (FIRST_JUMP, IMMEDIATE, CONTRIB_EXPLOSION) |
| `scripts/dsl-combined.py` | DSL v4 combined trailing stop engine (all positions) |
| `scripts/dsl-v4.py` | DSL v4 single-position engine (legacy, still works) |
| `scripts/sm-flip-check.py` | SM conviction flip detector |
| `scripts/wolf-monitor.py` | Watchdog — margin buffer + position health |
| `scripts/opportunity-scan.py` | Opportunity Scanner v5 (broken/optional) |
| `scripts/job-health-check.py` | Orphan DSL / stale cron detector |
