# DSL High Water Mode — Adoption Guide for All Skills

**Target:** Every Senpi skill should use DSL High Water Mode as the default DSL configuration.
**Spec:** https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md
**Status:** The DSL v5.2 engine does not yet support `lockMode: "pct_of_high_water"`. Until the engine update ships, all skills must use the legacy fallback tiers below.

---

## How to Apply (All Skills)

### Step 1: Add to your skill's dsl-profile.json or config

Add these fields to your DSL config section:

```json
{
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": <see per-skill table>,
  "tiers": <see per-skill High Water tiers>,
  "tiersLegacyFallback": <see per-skill fallback tiers>
}
```

### Step 2: Use fallback tiers in DSL state files (until engine update)

When creating DSL state files via `dsl-cli.py` or manually, use the `tiersLegacyFallback` tiers with standard `lockPct` fields. Do NOT include `lockMode` or `lockHwPct` — the current engine will error or ignore them.

### Step 3: After engine update

Once DSL v5.2 supports `pct_of_high_water`:
1. Switch state file tiers from `tiersLegacyFallback` to `tiers` (with `lockHwPct`)
2. Add `lockMode: "pct_of_high_water"` to state files
3. Existing positions on legacy tiers continue working — only new positions get High Water

---

## Per-Skill Configuration

### 🦬 BISON — Conviction Holder (widest tiers)

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 10,
  "floorBase": 0.03,
  "tiers": [
    {"triggerPct": 10,  "lockHwPct": 0,  "consecutiveBreachesRequired": 3},
    {"triggerPct": 20,  "lockHwPct": 25, "consecutiveBreachesRequired": 3},
    {"triggerPct": 30,  "lockHwPct": 40, "consecutiveBreachesRequired": 2},
    {"triggerPct": 50,  "lockHwPct": 60, "consecutiveBreachesRequired": 2},
    {"triggerPct": 75,  "lockHwPct": 75, "consecutiveBreachesRequired": 1},
    {"triggerPct": 100, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 1.5},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 15, "lockPct": 10, "retrace": 0.015},
    {"triggerPct": 25, "lockPct": 18, "retrace": 0.012},
    {"triggerPct": 40, "lockPct": 30, "retrace": 0.010},
    {"triggerPct": 60, "lockPct": 48, "retrace": 0.008},
    {"triggerPct": 80, "lockPct": 65, "retrace": 0.006},
    {"triggerPct": 100, "lockPct": 85, "retrace": 0.005}
  ]
}
```

---

### 🐍 COBRA — Triple Convergence

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "floorBase": 0.015,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 30, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 50, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 70, "consecutiveBreachesRequired": 2},
    {"triggerPct": 30, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 1.5},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 20, "lockPct": 14, "retrace": 0.012},
    {"triggerPct": 35, "lockPct": 25, "retrace": 0.010},
    {"triggerPct": 50, "lockPct": 40, "retrace": 0.008},
    {"triggerPct": 75, "lockPct": 60, "retrace": 0.006},
    {"triggerPct": 100, "lockPct": 82, "retrace": 0.005}
  ]
}
```

---

### 🦅 HAWK — Multi-Asset Best Signal

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "floorBase": 0.02,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 40, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 55, "consecutiveBreachesRequired": 2},
    {"triggerPct": 15, "lockHwPct": 75, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 2},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 15, "lockPct": 9,  "retrace": 0.012},
    {"triggerPct": 25, "lockPct": 17, "retrace": 0.010},
    {"triggerPct": 40, "lockPct": 30, "retrace": 0.008},
    {"triggerPct": 60, "lockPct": 48, "retrace": 0.006},
    {"triggerPct": 80, "lockPct": 65, "retrace": 0.005}
  ]
}
```

---

### 🦂 SCORPION — Whale Wallet Tracker

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "floorBase": 0.02,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 35, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 50, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 70, "consecutiveBreachesRequired": 2},
    {"triggerPct": 30, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 4,  "lockPct": 1.5},
    {"triggerPct": 8,  "lockPct": 4},
    {"triggerPct": 15, "lockPct": 10, "retrace": 0.012},
    {"triggerPct": 25, "lockPct": 18, "retrace": 0.010},
    {"triggerPct": 40, "lockPct": 32, "retrace": 0.008},
    {"triggerPct": 60, "lockPct": 50, "retrace": 0.006},
    {"triggerPct": 80, "lockPct": 68, "retrace": 0.005},
    {"triggerPct": 100, "lockPct": 88, "retrace": 0.004}
  ]
}
```

---

### 🐍 VIPER — Range-Bound Sniper

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 5,
  "floorBase": 0.015,
  "tiers": [
    {"triggerPct": 5,  "lockHwPct": 30, "consecutiveBreachesRequired": 3},
    {"triggerPct": 10, "lockHwPct": 50, "consecutiveBreachesRequired": 2},
    {"triggerPct": 15, "lockHwPct": 70, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 3,  "lockPct": 1},
    {"triggerPct": 5,  "lockPct": 3},
    {"triggerPct": 8,  "lockPct": 5, "retrace": 0.012},
    {"triggerPct": 12, "lockPct": 8, "retrace": 0.010},
    {"triggerPct": 18, "lockPct": 14, "retrace": 0.008},
    {"triggerPct": 25, "lockPct": 20, "retrace": 0.006}
  ]
}
```

---

### 👻 GHOST FOX — High Water Momentum

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 40, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 55, "consecutiveBreachesRequired": 2},
    {"triggerPct": 15, "lockHwPct": 75, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 1.5},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 15, "lockPct": 10, "retrace": 0.012},
    {"triggerPct": 25, "lockPct": 18, "retrace": 0.010},
    {"triggerPct": 40, "lockPct": 32, "retrace": 0.008},
    {"triggerPct": 60, "lockPct": 50, "retrace": 0.006},
    {"triggerPct": 80, "lockPct": 68, "retrace": 0.005},
    {"triggerPct": 100, "lockPct": 88, "retrace": 0.004}
  ]
}
```

---

### 🐍 MAMBA — Range Breakout Predator

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 5,
  "tiers": [
    {"triggerPct": 5,  "lockHwPct": 30, "consecutiveBreachesRequired": 3},
    {"triggerPct": 10, "lockHwPct": 50, "consecutiveBreachesRequired": 2},
    {"triggerPct": 15, "lockHwPct": 70, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 1.5},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 15, "lockPct": 10, "retrace": 0.012},
    {"triggerPct": 25, "lockPct": 18, "retrace": 0.010},
    {"triggerPct": 40, "lockPct": 32, "retrace": 0.008},
    {"triggerPct": 60, "lockPct": 50, "retrace": 0.006},
    {"triggerPct": 80, "lockPct": 68, "retrace": 0.005},
    {"triggerPct": 100, "lockPct": 88, "retrace": 0.004}
  ]
}
```

---

### 🐊 CROC — Funding Rate Arbitrage

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 8,
  "floorBase": 0.02,
  "tiers": [
    {"triggerPct": 8,  "lockHwPct": 25, "consecutiveBreachesRequired": 3},
    {"triggerPct": 15, "lockHwPct": 45, "consecutiveBreachesRequired": 2},
    {"triggerPct": 25, "lockHwPct": 65, "consecutiveBreachesRequired": 2},
    {"triggerPct": 40, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 2},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 20, "lockPct": 14, "retrace": 0.012},
    {"triggerPct": 30, "lockPct": 24, "retrace": 0.010},
    {"triggerPct": 50, "lockPct": 44, "retrace": 0.008},
    {"triggerPct": 75, "lockPct": 60, "retrace": 0.006}
  ]
}
```

---

### 🦈 SHARK — SM Consensus + Cascades

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "floorBase": 0.018,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 35, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 55, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 75, "consecutiveBreachesRequired": 1},
    {"triggerPct": 30, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 2},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 20, "lockPct": 14, "retrace": 0.012},
    {"triggerPct": 30, "lockPct": 24, "retrace": 0.010},
    {"triggerPct": 50, "lockPct": 44, "retrace": 0.008},
    {"triggerPct": 75, "lockPct": 60, "retrace": 0.006},
    {"triggerPct": 100, "lockPct": 85, "retrace": 0.005}
  ]
}
```

---

### 🦊 FERAL FOX v2 — High Conviction Momentum

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "floorBase": 0.015,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 40, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 55, "consecutiveBreachesRequired": 2},
    {"triggerPct": 15, "lockHwPct": 75, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 1.5},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 15, "lockPct": 10, "retrace": 0.012},
    {"triggerPct": 25, "lockPct": 18, "retrace": 0.010},
    {"triggerPct": 40, "lockPct": 32, "retrace": 0.008},
    {"triggerPct": 60, "lockPct": 50, "retrace": 0.006},
    {"triggerPct": 80, "lockPct": 68, "retrace": 0.005},
    {"triggerPct": 100, "lockPct": 88, "retrace": 0.004}
  ]
}
```

---

### 🐺 DIRE WOLF v2 — Sniper Mode

```json
"dsl": {
  "_spec": "https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md",
  "lockMode": "pct_of_high_water",
  "phase2TriggerRoe": 7,
  "tiers": [
    {"triggerPct": 7,  "lockHwPct": 40, "consecutiveBreachesRequired": 3},
    {"triggerPct": 12, "lockHwPct": 55, "consecutiveBreachesRequired": 2},
    {"triggerPct": 15, "lockHwPct": 75, "consecutiveBreachesRequired": 2},
    {"triggerPct": 20, "lockHwPct": 85, "consecutiveBreachesRequired": 1}
  ],
  "tiersLegacyFallback": [
    {"triggerPct": 5,  "lockPct": 1.5},
    {"triggerPct": 10, "lockPct": 5},
    {"triggerPct": 15, "lockPct": 10, "retrace": 0.012},
    {"triggerPct": 25, "lockPct": 18, "retrace": 0.010},
    {"triggerPct": 40, "lockPct": 32, "retrace": 0.008},
    {"triggerPct": 60, "lockPct": 50, "retrace": 0.006},
    {"triggerPct": 80, "lockPct": 68, "retrace": 0.005},
    {"triggerPct": 100, "lockPct": 88, "retrace": 0.004}
  ]
}
```

---

## Workaround Instructions for Agents

Add this to every skill's SKILL.md or cron mandate:

```
DSL CONFIGURATION:
Target: DSL High Water Mode (pct_of_high_water).
Spec: https://github.com/Senpi-ai/senpi-skills/blob/main/dsl-dynamic-stop-loss/dsl-high-water-spec%201.0.md

CURRENT WORKAROUND (until DSL engine supports lockMode):
Use the tiersLegacyFallback tiers from config with standard lockPct fields.
Do NOT include lockMode or lockHwPct in state files — the current engine will error.

AFTER ENGINE UPDATE:
Switch to the tiers array with lockHwPct fields.
Add lockMode: "pct_of_high_water" to every new state file.
Existing positions on legacy tiers continue working unchanged.
```

## Tier Design Philosophy

| Skill Type | Phase 2 Trigger | T1 Lock | 85% Trail At | Why |
|---|---|---|---|---|
| Momentum (FOX, DIRE WOLF, GHOST FOX, HAWK) | +7% ROE | 40% HW | +20% ROE | Fast entries, need quick trailing |
| Convergence (COBRA, SHARK) | +7% ROE | 30-35% HW | +30% ROE | Multiple signals, moderate patience |
| Range (VIPER, MAMBA) | +5% ROE | 30% HW | +20% ROE | Smaller moves, protect early |
| Funding (CROC) | +8% ROE | 25% HW | +40% ROE | Funding arb is slow but structural |
| Conviction (BISON) | +10% ROE | 0% HW | +100% ROE | Multi-day holds need maximum room |
| Whale tracking (SCORPION) | +7% ROE | 35% HW | +30% ROE | Following whale timing, moderate |
