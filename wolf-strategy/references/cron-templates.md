[cron-templates.md](https://github.com/user-attachments/files/25528050/cron-templates.md)
# WOLF v5 Cron Templates

All crons use OpenClaw's systemEvent format:
```json
{
  "name": "...",
  "schedule": { "kind": "every", "everyMs": ... },
  "sessionTarget": "main",
  "wakeMode": "now",
  "payload": { "kind": "systemEvent", "text": "..." }
}
```

**These are OpenClaw crons, NOT Senpi crons.** They wake the agent with a mandate text that the agent executes.

Replace these placeholders in all templates:
- `{WALLET}` — strategy wallet address (0x...)
- `{STRATEGY_SHORT}` — first 8 chars of strategy UUID
- `{MARGIN}` — margin per slot in USD (e.g. 2000)
- `{LEVERAGE}` — default leverage (e.g. 10)
- `{SLOTS}` — max concurrent positions (e.g. 3)
- `{DELEVER_THRESHOLD}` — auto-delever account threshold (e.g. 6000)
- `{TELEGRAM}` — telegram:CHAT_ID (e.g. telegram:5183731261)
- `{SCRIPTS}` — path to scripts dir (e.g. /data/workspace/skills/wolf-strategy/scripts)

---

## 1. Emerging Movers (every 90s)

```
WOLF v5 Scanner: Run `PYTHONUNBUFFERED=1 python3 {SCRIPTS}/emerging-movers.py`, parse JSON.

MANDATE: Enter EARLY on first jumps — before the peak, not at it. Speed is edge.

SIGNAL PRIORITY (act on the FIRST one that fires):

1. **FIRST_JUMP** (⚡ highest priority): `isFirstJump: true`. Asset jumped 10+ ranks from #25+ AND was not in previous top 50 (or was ≥ #30). ENTER IMMEDIATELY — ${MARGIN} margin, {LEVERAGE}x leverage. 2+ reasons is enough. vel > 0 is enough. Do NOT wait for confirmation. Do NOT require clean rank history. This IS the signal.

2. **CONTRIB_EXPLOSION** (💥): `isContribExplosion: true`. 3x+ contrib spike from rank #20+. ENTER — ${MARGIN} margin, {LEVERAGE}x leverage. NEVER downgrade for erratic history. Often accompanies FIRST_JUMP for double confirmation.

3. **IMMEDIATE_MOVER**: `isImmediate: true` (but not FIRST_JUMP). 10+ rank jump from #25+ in ONE scan. ENTER if not downgraded (check `erratic: false`, `lowVelocity: false`). ${MARGIN} margin, {LEVERAGE}x leverage.

4. **NEW_ENTRY_DEEP**: Asset appears in top 20 from nowhere. ENTER — ${MARGIN} margin, {LEVERAGE}x leverage.

5. **DEEP_CLIMBER**: `isDeepClimber: true`, steady climb, vel ≥ 0.03, 3+ reasons. Enter when it crosses top 20.

RULES:
- Wallet: {WALLET} (strategy {STRATEGY_SHORT}). XYZ positions use leverageType ISOLATED, dex "xyz".
- Max {SLOTS} positions. Min 7x leverage (skip assets below 7x — check max-leverage.json).
- Alert user on Telegram ({TELEGRAM}) after every action.
- **ANTI-PATTERN: NEVER enter assets already at rank #1-10 for 2+ scans.** That's the top, not the entry.
- **ANTI-PATTERN: 4+ reasons at rank #5 = SKIP.** Asset already peaked.
- **DEAD WEIGHT RULE**: Negative ROE + SM conviction against it for 30+ min → CUT immediately.
- **ROTATION RULE**: If slots FULL and FIRST_JUMP fires → compare against weakest position. If weakest has flat/negative ROE with SM conv 0-1 → CUT weakest, OPEN new. If weakest is Tier 2+ or SM conv 3+ → HOLD.
- If no actionable signals → HEARTBEAT_OK.
- **AUTO-DELEVER**: Account below ${DELEVER_THRESHOLD} → max {SLOTS-1} positions, close weakest.
```

---

## 2. DSL Combined Runner (every 3min)

```
WOLF DSL: Run `DSL_STATE_DIR=/data/workspace PYTHONUNBUFFERED=1 python3 {SCRIPTS}/dsl-combined.py`, parse JSON.

This checks ALL active positions in one pass. Parse the `results` array.

FOR EACH position in results:
- If `closed: true` → alert user on Telegram ({TELEGRAM}) with asset, direction, close_reason, upnl. Evaluate: empty slot for next signal?
- If `tier_changed: true` → note the tier upgrade (useful for portfolio context).
- If `phase1_autocut: true` and `closed: true` → position was cut for Phase 1 timeout (90min) or weak peak (45min). Alert user.
- If `status: "pending_close"` → close failed, will retry next run. Alert user if first occurrence.

If `any_closed: true` → at least one position was closed this run. Check for new signals.
If all positions active with no alerts → HEARTBEAT_OK.
```

---

## 3. SM Flip Detector (every 5min)

```
WOLF SM Check: Run `python3 {SCRIPTS}/sm-flip-check.py`, parse JSON.

If any alert has conviction 4+ in the OPPOSITE direction of our position with 100+ traders → CUT the position immediately (don't flip, just close and free the slot). Set DSL state active: false.
Conviction 2-3 = note but don't act unless position is also in negative ROE.
Alert user on Telegram ({TELEGRAM}) for any cuts.
If hasFlipSignal=false → HEARTBEAT_OK.
```

---

## 4. Watchdog (every 5min)

```
WOLF Watchdog: Run `PYTHONUNBUFFERED=1 timeout 45 python3 {SCRIPTS}/wolf-monitor.py`. Parse JSON output.

KEY CHECKS:
1. **Cross-margin buffer** (`crypto_liq_buffer_pct`): If <50% → WARNING to user. If <30% → CRITICAL, consider closing weakest position.
2. **Position alerts**: Any alert with level=CRITICAL → immediate Telegram alert ({TELEGRAM}). WARNING → alert if new (don't repeat same warning within 15min).
3. **Rotation check**: Compare each position's ROE. If any position is -15%+ ROE AND emerging movers show a strong climber (top 10, 3+ reasons) we DON'T hold → suggest rotation to user.
4. **XYZ isolated liq**: If liq_distance_pct < 15% → alert user.
5. Save output to /data/workspace/watchdog-last.json for dedup.

If no alerts needed → HEARTBEAT_OK.
```

---

## 5. Portfolio Update (every 15min)

```
WOLF portfolio update: Get clearinghouse state for wallet {WALLET}. Send user a concise Telegram update ({TELEGRAM}). Code block table format. Include account value, each position (asset, direction, ROE, PnL, DSL tier), and slot usage ({SLOTS} max).
```

---

## 6. Health Check (every 10min)

```
WOLF Health Check: Run `PYTHONUNBUFFERED=1 python3 {SCRIPTS}/job-health-check.py`, parse JSON.

If any CRITICAL issues → fix immediately:
- Orphan DSL state files (active: true but no matching position) → set active: false
- Positions without DSL state files → create dsl-state-WOLF-{ASSET}.json with correct config
- Direction mismatches → fix state file direction

Alert user on Telegram ({TELEGRAM}) for critical issues.
If only WARNINGs → fix silently.
If no issues → HEARTBEAT_OK.

NOTE: The combined DSL runner handles all positions, so there are no per-position crons to check. Health check only validates state files vs actual positions.
```

---

## 7. Opportunity Scanner (every 15min) — OPTIONAL

```
WOLF scanner: Run `PYTHONUNBUFFERED=1 timeout 180 python3 {SCRIPTS}/opportunity-scan.py 2>/dev/null`. Read /data/workspace/wolf-strategy.json for rules. Wallet: {WALLET} (strategy {STRATEGY_SHORT}). Max {SLOTS} concurrent positions, ${MARGIN} margin each, {LEVERAGE}x leverage. XYZ positions use leverageType ISOLATED on same wallet. Threshold 175+. Check existing positions before opening. If good opportunity → open position, create DSL state file (dsl-state-WOLF-{ASSET}.json), alert user ({TELEGRAM}). Otherwise HEARTBEAT_OK. AUTO-DELEVER: If account below ${DELEVER_THRESHOLD} → max {SLOTS-1} positions only.
```

**NOTE:** The opportunity scanner has reliability issues. Emerging Movers (cron #1) is the primary and proven entry source. This cron is optional.

---

## v5 Changes from v4

| Change | v4 | v5 |
|--------|----|----|
| Scanner interval | 60s | **90s** (reduces token burn) |
| Top signal | IMMEDIATE_MOVER | **FIRST_JUMP** (enter before confirmation) |
| Entry threshold | 4+ reasons, vel ≥ 0.03 | **2+ reasons, vel > 0 for first jumps** |
| DSL architecture | Per-position crons (create/destroy) | **Combined runner** (one cron, all positions) |
| Phase 1 max | No limit | **90min hard cap, 45min weak peak cut** |
| Min leverage | Any | **7x minimum** |
| Erratic filter | Full history | **Exclude current jump for FIRST_JUMP/IMMEDIATE** |
| CONTRIB_EXPLOSION | Could be downgraded | **Never downgraded** |
