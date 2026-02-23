# WOLF Strategy v4.0

Fully autonomous 2-3 slot trading strategy for Hyperliquid perps. The WOLF hunts for its human — scans, enters, exits, and rotates positions without asking permission.

## What's New in v4

- **2-3 slots** — scales with account size (2 slots under $6k, 3 slots above)
- **Auto-delever** — if account drops below 3-slot threshold, immediately reverts to 2 and cuts weakest
- **Removed conviction gate** — rank climb velocity IS the entry signal, conviction is lagging. Successfully entered APT (25 traders, conv 0), SNDK (14 traders) as winners
- **XYZ equities support** — isolated margin, `xyz:` prefix, trader count exempt
- **Oversold decline rule** — skip short entries when RSI < 30 + extended 24h move
- **Tighter DSL tiers** — 4 tiers at 5/10/15/20% ROE (not 6 at 10/20/30/50/75/100%). Locks profit earlier on the 5-20% moves that actually happen
- **Token optimization** — skip redundant checks when data is <3 min old
- **SM Flip exit** — conviction 4+ opposite direction with 100+ traders = cut immediately
- **DSL state schema documented** — exact JSON with all critical field notes
- **Known bugs section** — dryRun actually executes, health check can't see XYZ, and more

## Proven Results

**+$1,500 realized across 20+ trades, 67% win rate** on $6.5k→$7k budget.

Top winners: HYPE SHORT +$560, XRP SHORT +$303, ETH SHORT +$274, SNDK SHORT +$237, LIT SHORT +$205, APT SHORT +$178.

## Requires

- [DSL (Dynamic Stop Loss)](../dsl-dynamic-stop-loss/SKILL.md)
- [Opportunity Scanner](../opportunity-scanner/SKILL.md)
- [Emerging Movers Detector](../emerging-movers/SKILL.md)

## Install

Download [SKILL.md](SKILL.md) and send it to your Senpi agent with: **"Here are some new superpowers"**

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.0 | 2026-02-23 | 2-3 slots, auto-delever, removed conviction gate, XYZ support, oversold decline rule, tighter DSL tiers, token optimization, SM flip exit |
| v3.1 | 2026-02-23 | Budget-scaled parameters, autonomy rules, aggressive rotation |
| v3.0 | 2026-02-23 | Initial release. 2-slot, IMMEDIATE_MOVER entries, proven +$750 |
