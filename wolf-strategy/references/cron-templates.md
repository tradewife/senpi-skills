# WOLF v4 Cron Templates

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

## 1. Emerging Movers (every 60s)

```
WOLF v3 Scanner: Run `PYTHONUNBUFFERED=1 python3 {SCRIPTS}/emerging-movers.py`, parse JSON.

MANDATE: Hunt runners before they peak. v3 IMMEDIATE signals + DSL.
1. **IMMEDIATE_MOVER**: 10+ rank jump from #25+ in ONE scan → OPEN ${MARGIN} margin, {LEVERAGE}x leverage, DSL on. Act on FIRST jump.
2. **NEW_ENTRY_DEEP**: Appears in top 20 from nowhere → OPEN ${MARGIN} margin, {LEVERAGE}x leverage, DSL on.
3. **CONTRIB_EXPLOSION**: 3x+ contrib in one scan → OPEN ${MARGIN} margin, {LEVERAGE}x leverage, DSL on.
4. Wallet: {WALLET} (strategy {STRATEGY_SHORT}). XYZ positions use leverageType ISOLATED on same wallet.
5. Max {SLOTS} positions. Alert user on Telegram ({TELEGRAM}).
6. Negative velocity or already-peaked signals = SKIP. Empty slot > mediocre position.
7. **DEAD WEIGHT RULE**: If any open position has negative ROE AND SM conviction is against it (flipped, conv 1+) for 30+ minutes → CUT immediately and free the slot.
8. **ROTATION RULE**: If slots are FULL and a new IMMEDIATE fires, compare it against current positions. Score: reason count + rank jump magnitude + contrib velocity. If new signal scores higher than weakest position's current momentum (ROE trend, SM conviction, contrib rank) → CUT weakest, OPEN new. Factors favoring rotation: new signal has 4+ reasons, weakest position is flat/negative ROE, weakest has low SM conviction (0-1). Factors favoring hold: current position is trending up with good ROE, SM conv 3+.
9. If no actionable signals → HEARTBEAT_OK.
10. **AUTO-DELEVER**: If account drops below ${DELEVER_THRESHOLD} → revert to max {SLOTS-1} positions, close weakest if {SLOTS} open.
```

---

## 2. DSL Per-Position (every 180s) — Created per trade

```
[DSL] Run DSL check for {ASSET}: `DSL_STATE_FILE=/data/workspace/dsl-state-WOLF-{ASSET}.json PYTHONUNBUFFERED=1 python3 {SCRIPTS}/dsl-v4.py`. Parse JSON output. If close_triggered=true, close {ASSET} (coin={COIN}, strategyWalletAddress={WALLET}), alert user on Telegram ({TELEGRAM}), deactivate state file, disable this cron. If active=false, HEARTBEAT_OK.
```

**Note:** `{COIN}` = asset name for crypto (e.g. `PAXG`), or `xyz:ASSET` for XYZ assets (e.g. `xyz:SILVER`).

---

## 3. SM Flip Detector (every 5min)

```
WOLF SM Check (warning-only): Run `python3 {SCRIPTS}/sm-flip-check.py`, parse JSON. If any alert has conviction 4+ SHORT against our LONG (or vice versa) with 100+ traders → CUT the position (don't flip, just close and free the slot for runners). conviction 2-3 = note but don't act. If hasFlipSignal=false → HEARTBEAT_OK.
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
WOLF portfolio update: Get clearinghouse state for wallet {WALLET}. Send user a concise Telegram update ({TELEGRAM}). Code block table format. Include account value and position summary.
```

---

## 6. Health Check (every 10min)

```
WOLF Health Check: Run `PYTHONUNBUFFERED=1 python3 {SCRIPTS}/job-health-check.py`, parse JSON.

If any CRITICAL issues → fix immediately (deactivate orphan DSLs, create missing DSLs for unprotected positions, fix direction mismatches). Alert user on Telegram ({TELEGRAM}) for critical issues.
If only WARNINGs → fix silently (deactivate orphans, note stale crons).
If no issues → HEARTBEAT_OK.
```

---

## 7. Opportunity Scanner (every 15min)

```
WOLF scanner: Run `PYTHONUNBUFFERED=1 timeout 180 python3 {SCRIPTS}/opportunity-scan.py 2>/dev/null`. Read /data/workspace/wolf-strategy.json for rules. Wallet: {WALLET} (strategy {STRATEGY_SHORT}). Max {SLOTS} concurrent positions, ${MARGIN} margin each, {LEVERAGE}x leverage. XYZ positions use leverageType ISOLATED on same wallet. Threshold 175+. Check existing positions before opening. If good opportunity → open position, create DSL state file (dsl-state-WOLF-{ASSET}.json), create DSL cron, alert user ({TELEGRAM}). Otherwise HEARTBEAT_OK. AUTO-DELEVER: If account below ${DELEVER_THRESHOLD} → max {SLOTS-1} positions only.
```
