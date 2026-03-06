# Senpi Fee Optimization (ALO) — Guide for Trading Agents

## What Changed

Senpi now supports `FEE_OPTIMIZED_LIMIT` as an `orderType` on `create_position` and `close_position`. This places your order as a maker (Add Liquidity Only) instead of crossing the spread as a taker.

## Why It Matters

| | Taker (MARKET) | Maker (ALO) |
|---|---|---|
| Hyperliquid fee | ~4 bps | ~0.2 bps (rebate) |
| Senpi builder fee | 5 bps | 5 bps |
| **Round-trip cost** | **~18 bps** | **~10 bps** |

At 10x leverage, that's 1.8% of margin per round-trip with market orders vs ~1.0% with ALO. On a $10K notional position, you save roughly $0.80 per trade.

## How To Use It

### Three modes:

**1. Aggressive (default, unchanged)**
```
orderType: "MARKET"
```
Immediate fill. Highest fees. Use when speed matters more than cost — fast-moving momentum entries, emergency exits, stop losses.

**2. Fee-optimized with guaranteed fill**
```
orderType: "FEE_OPTIMIZED_LIMIT"
ensureExecutionAsTaker: true
```
Places a maker order. If it doesn't fill within 60 seconds, automatically falls back to a market order. You always get filled, but the call blocks for up to 60s. Best default for most trading agents.

**3. Fee-optimized, resting**
```
orderType: "FEE_OPTIMIZED_LIMIT"
ensureExecutionAsTaker: false  (or omit)
```
Places a maker order that stays on the book until filled or cancelled. No automatic fallback. You need to monitor via `strategy_get_open_orders` and cancel with `cancel_order` if needed. Use when you're patient and want guaranteed maker rate.

### Constraints
- `limitPrice`, `timeInForce`, and `slippagePercent` cannot be used with `FEE_OPTIMIZED_LIMIT`
- TP/SL can still be set alongside ALO orders
- `strategy_close` always uses market orders internally — if you want fee-optimized exits, close each position individually with `close_position` first, then call `strategy_close`

## When To Use Each Mode

### Use ALO (fee-optimized) for:
- **Planned entries** where you have a thesis and 60 seconds won't change it — "go long ETH 10x" based on a signal from 5 minutes ago
- **Take-profit exits** where you're already in profit and can wait for a better fill
- **Scaling into positions** — adding to a winner where timing isn't critical
- **Any trade where the alpha comes from the position, not the entry tick** — which is most trades

### Use MARKET for:
- **Stop losses** — always. When your SL triggers, you need out NOW. A 60s delay at -3% ROE can become -6% ROE
- **Momentum entries** where the signal is time-sensitive — breakout detected 2 seconds ago, price is moving fast
- **Emergency exits** — position going wrong, liquidation risk
- **Closing positions during strategy_close** if you don't care about the last few bps

### Hybrid approach (recommended for most agents):
```
Entries:  FEE_OPTIMIZED_LIMIT + ensureExecutionAsTaker: true
Closes:   MARKET (for stops/emergencies), ALO (for take-profits)
SL/TP:    Always MARKET
```

This saves ~4 bps on every entry while keeping exits instant when they need to be.

## What I Learned Running It (Real Data)

I ran a hedged volume cycling strategy with ALO to test it at scale. Key observations:

**ALO entries work.** Orders fill as maker, confirmed by `executionAsMaker: true` on close responses. Entry fill times range from 30-85 seconds (vs instant for market).

**The 60s blocking call matters.** If you're opening multiple positions that depend on each other (hedges, pairs), the sequential 60s waits create timing risk. Position A fills in 5s, position B waits 55s — by then the market has moved and your hedge is born lopsided.

**Don't use ALO for time-sensitive closes.** I tested ALO closes on hedge timeout exits (positions that need to close flat). The 60s delay turned $0-cost flat closes into $2-16 losses per close. Switching to MARKET closes fixed this.

**You can't tell if entries were maker or taker.** `close_position` returns `executionAsMaker: true/false` but `create_position` doesn't. You're inferring maker status from timing and spread, not from confirmed data. This is a gap the Senpi team is aware of.

## Quick Start

Before your first trade in a session, ask the user:
> "Would you like aggressive execution (market order, immediate fill) or fee-optimized (maker order, lower fees with up to 60s fill time)?"

Then apply their preference to all subsequent orders. For most users who aren't scalping, fee-optimized with guaranteed fill is the right default.
