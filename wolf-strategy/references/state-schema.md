# WOLF v4 State & Config Schemas

## DSL State File (`dsl-state-WOLF-{ASSET}.json`)

Created per position, read by `dsl-v4.py` via `DSL_STATE_FILE` env var.

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
  "createdAt": "2026-02-23T10:00:00Z",
  "hwTimestamp": "2026-02-23T10:05:00Z",
  "lastCheck": "2026-02-23T10:06:00Z",
  "lastPrice": 0.8100,
  "consecutiveFetchFailures": 0,
  "pendingClose": false,
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
    "minROE": 8.0,
    "priceRangePct": 1.0
  }
}
```

### Required Fields

| Field | Type | Description |
|---|---|---|
| `active` | boolean | `true` = DSL is running. Set to `false` on close. |
| `asset` | string | Asset name (e.g. "APT", "PAXG"). No `xyz:` prefix. |
| `direction` | string | "LONG" or "SHORT" |
| `entryPrice` | number | Position entry price |
| `leverage` | number | Position leverage |
| `size` | number | Absolute position size (units) |
| `wallet` | string | Strategy wallet address |
| `dex` | string\|null | "xyz" for XYZ assets, null for crypto |
| `highWaterPrice` | number | Best price seen (highest for LONG, lowest for SHORT) |
| `phase` | number | 1 = pre-tier, 2 = tier-based trailing |
| `currentTierIndex` | number | Current tier (0-3), or 0 if none |
| `tierFloorPrice` | number\|null | Locked tier floor price |
| `currentBreachCount` | number | Consecutive floor breaches |
| `floorPrice` | number | Effective floor (auto-calculated) |
| `tiers` | array | 4-tier config array |

### Optional Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `createdAt` | string | — | ISO timestamp for elapsed time calc |
| `hwTimestamp` | string | — | When HW was last updated (for stagnation) |
| `pendingClose` | boolean | false | Retry close on next run |
| `consecutiveFetchFailures` | number | 0 | Auto-deactivate at 10 |
| `breachDecay` | string | "hard" | "hard" = reset to 0, "soft" = decay by 1 |
| `closeRetries` | number | 2 | Close API retry count |
| `maxFetchFailures` | number | 10 | Failures before auto-deactivate |
| `stagnation` | object | enabled | Stagnation take-profit config |

---

## wolf-strategy.json (Strategy Config)

Created by `wolf-setup.py`, read by cron mandates.

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
  "strategyId": "uuid",
  "telegramChatId": 5183731261,
  "telegramTarget": "telegram:5183731261"
}
```

---

## Key Gotchas

1. **`triggerPct` not `threshold`** — Tiers use `triggerPct: 5` (percentage), NOT `threshold: 0.05` (decimal). The DSL script expects percentage values.

2. **`lockPct` not `retracePct`** — Tiers use `lockPct: 50` (lock 50% of HW profit), NOT `retracePct`. The lock percentage determines the trailing floor.

3. **`active` is boolean** — Use `"active": true`, NOT `"status": "active"`. The DSL script checks `state.get("active")`.

4. **`DSL_STATE_FILE` env var ONLY** — The DSL script reads state file path from the `DSL_STATE_FILE` environment variable. Positional args are silently ignored. Always set it: `DSL_STATE_FILE=/path/to/file.json python3 dsl-v4.py`

5. **`absoluteFloor` is auto-calculated** — The DSL script recalculates it from entryPrice, retraceThreshold, and leverage on every run. You only need to set `phase1.retraceThreshold` (default: 5 = 5% ROE).

6. **XYZ assets** — Set `dex: "xyz"` in state file. Use `coin=xyz:ASSET` when closing (e.g. `xyz:SILVER`). Use `leverageType: "ISOLATED"` when opening.

7. **4 tiers, not 6** — The proven tier structure is 5/10/15/20% ROE with 50/65/75/85% locks. NOT the old 6-tier (10/20/30/50/75/100%) version.
