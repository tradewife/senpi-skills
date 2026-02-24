#!/usr/bin/env python3
"""
WOLF v4 Setup Wizard
Sets up the WOLF autonomous trading strategy.
Calculates all parameters from budget, fetches max-leverage data,
and outputs config + cron templates.

Usage:
  # Agent passes what it knows, only asks user for budget:
  python3 wolf-setup.py --wallet 0x... --strategy-id UUID --chat-id 12345 --budget 6500

  # Interactive mode (prompts for everything):
  python3 wolf-setup.py
"""
import json, subprocess, sys, os, math, argparse

WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", "/data/workspace")
CONFIG_FILE = os.path.join(WORKSPACE, "wolf-strategy.json")
MAX_LEV_FILE = os.path.join(WORKSPACE, "max-leverage.json")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Parse CLI args — agent passes what it already knows
parser = argparse.ArgumentParser(description="WOLF v4 Setup")
parser.add_argument("--wallet", help="Strategy wallet address (0x...)")
parser.add_argument("--strategy-id", help="Strategy ID (UUID)")
parser.add_argument("--budget", type=float, help="Trading budget in USD (min $500)")
parser.add_argument("--chat-id", type=int, help="Telegram chat ID")
args = parser.parse_args()

def ask(prompt, default=None, validator=None):
    while True:
        suffix = f" [{default}]" if default else ""
        val = input(f"{prompt}{suffix}: ").strip()
        if not val and default:
            val = str(default)
        if validator:
            try:
                return validator(val)
            except Exception as e:
                print(f"  Invalid: {e}")
        elif val:
            return val
        else:
            print("  Required.")

def validate_wallet(v):
    if not v.startswith("0x") or len(v) != 42:
        raise ValueError("Must be 0x... (42 chars)")
    return v

def validate_uuid(v):
    parts = v.replace("-", "")
    if len(parts) != 32:
        raise ValueError("Must be a UUID (32 hex chars)")
    return v

def validate_budget(v):
    b = float(v)
    if b < 500:
        raise ValueError("Minimum budget is $500")
    return b

def validate_chat_id(v):
    return int(v)

print("=" * 60)
print("  WOLF v4 — Autonomous Trading Strategy Setup")
print("=" * 60)
print()

# Use CLI args if provided, otherwise prompt
wallet = args.wallet or ask("Strategy wallet address (0x...)", validator=validate_wallet)
if args.wallet:
    validate_wallet(args.wallet)

strategy_id = args.strategy_id or ask("Strategy ID (UUID)", validator=validate_uuid)
if args.strategy_id:
    validate_uuid(args.strategy_id)

budget = args.budget or ask("Trading budget (USD, min $500)", validator=validate_budget)
if args.budget:
    validate_budget(str(args.budget))

chat_id = args.chat_id or ask("Telegram chat ID (numeric)", validator=validate_chat_id)
if args.chat_id:
    validate_chat_id(str(args.chat_id))

# Calculate parameters
if budget < 3000:
    slots = 2
elif budget < 6000:
    slots = 2
elif budget < 10000:
    slots = 3
else:
    slots = 3

margin_per_slot = round(budget * 0.30, 2)
margin_buffer = round(budget * (1 - 0.30 * slots), 2)
daily_loss_limit = round(budget * -0.15, 2)
drawdown_cap = round(budget * -0.30, 2)

if budget < 1000:
    default_leverage = 5
elif budget < 5000:
    default_leverage = 7
elif budget < 15000:
    default_leverage = 10
else:
    default_leverage = 10

notional_per_slot = round(margin_per_slot * default_leverage, 2)

auto_delever_threshold = 6000 if slots == 3 else 3000

config = {
    "budget": budget,
    "slots": slots,
    "marginPerSlot": margin_per_slot,
    "marginBuffer": margin_buffer,
    "defaultLeverage": default_leverage,
    "maxLeverage": 20,
    "notionalPerSlot": notional_per_slot,
    "dailyLossLimit": daily_loss_limit,
    "drawdownCap": drawdown_cap,
    "autoDeleverThreshold": auto_delever_threshold,
    "wallet": wallet,
    "strategyId": strategy_id,
    "telegramChatId": chat_id,
    "telegramTarget": f"telegram:{chat_id}",
}

# Save config
with open(CONFIG_FILE, "w") as f:
    json.dump(config, f, indent=2)
print(f"\n✅ Config saved to {CONFIG_FILE}")

# Fetch max-leverage from Hyperliquid
print("\nFetching max-leverage data from Hyperliquid...")
try:
    r = subprocess.run(
        ["curl", "-s", "https://api.hyperliquid.xyz/info",
         "-H", "Content-Type: application/json",
         "-d", '{"type":"meta"}'],
        capture_output=True, text=True, timeout=30
    )
    meta = json.loads(r.stdout)
    max_lev = {}
    for asset in meta.get("universe", []):
        name = asset["name"]
        max_lev[name] = asset.get("maxLeverage", 50)
    with open(MAX_LEV_FILE, "w") as f:
        json.dump(max_lev, f, indent=2)
    print(f"✅ Max leverage data saved ({len(max_lev)} assets) to {MAX_LEV_FILE}")
except Exception as e:
    print(f"⚠️  Failed to fetch max-leverage: {e}")
    print("   You can manually fetch later.")

# Build cron templates
tg = f"telegram:{chat_id}"
margin_str = str(int(margin_per_slot))

cron_templates = {
    "emerging_movers": {
        "name": "WOLF Emerging Movers v3 (60s)",
        "schedule": {"kind": "every", "everyMs": 60000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"WOLF v3 Scanner: Run `PYTHONUNBUFFERED=1 python3 {SCRIPTS_DIR}/emerging-movers.py`, parse JSON.\n\nMANDATE: Hunt runners before they peak. v3 IMMEDIATE signals + DSL.\n1. **IMMEDIATE_MOVER**: 10+ rank jump from #25+ in ONE scan → OPEN ${margin_str} margin, {default_leverage}x leverage, DSL on. Act on FIRST jump.\n2. **NEW_ENTRY_DEEP**: Appears in top 20 from nowhere → OPEN ${margin_str} margin, {default_leverage}x leverage, DSL on.\n3. **CONTRIB_EXPLOSION**: 3x+ contrib in one scan → OPEN ${margin_str} margin, {default_leverage}x leverage, DSL on.\n4. Wallet: {wallet} (strategy {strategy_id[:8]}). XYZ positions use leverageType ISOLATED on same wallet.\n5. Max {slots} positions. Alert user on Telegram ({tg}).\n6. Negative velocity or already-peaked signals = SKIP. Empty slot > mediocre position.\n7. **DEAD WEIGHT RULE**: If any open position has negative ROE AND SM conviction is against it (flipped, conv 1+) for 30+ minutes → CUT immediately and free the slot.\n8. **ROTATION RULE**: If slots are FULL and a new IMMEDIATE fires, compare it against current positions. Score: reason count + rank jump magnitude + contrib velocity. If new signal scores higher than weakest position's current momentum (ROE trend, SM conviction, contrib rank) → CUT weakest, OPEN new. Factors favoring rotation: new signal has 4+ reasons, weakest position is flat/negative ROE, weakest has low SM conviction (0-1). Factors favoring hold: current position is trending up with good ROE, SM conv 3+.\n9. If no actionable signals → HEARTBEAT_OK.\n10. **AUTO-DELEVER**: If account drops below ${auto_delever_threshold:,} → revert to max {slots - 1} positions, close weakest if {slots} open."
        }
    },
    "dsl_template": {
        "name": "DSL {ASSET} 180s",
        "schedule": {"kind": "every", "everyMs": 180000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"[DSL] Run DSL check for {{ASSET}}: `DSL_STATE_FILE=/data/workspace/dsl-state-WOLF-{{ASSET}}.json PYTHONUNBUFFERED=1 python3 {SCRIPTS_DIR}/dsl-v4.py`. Parse JSON output. If close_triggered=true, close {{ASSET}} (coin={{COIN}}, strategyWalletAddress={wallet}), alert user on Telegram ({tg}), deactivate state file, disable this cron. If active=false, HEARTBEAT_OK."
        }
    },
    "sm_flip": {
        "name": "WOLF SM Flip Detector (5min)",
        "schedule": {"kind": "every", "everyMs": 300000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"WOLF SM Check (warning-only): Run `python3 {SCRIPTS_DIR}/sm-flip-check.py`, parse JSON. If any alert has conviction 4+ SHORT against our LONG (or vice versa) with 100+ traders → CUT the position (don't flip, just close and free the slot for runners). conviction 2-3 = note but don't act. If hasFlipSignal=false → HEARTBEAT_OK."
        }
    },
    "watchdog": {
        "name": "WOLF Watchdog (5min)",
        "schedule": {"kind": "every", "everyMs": 300000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"WOLF Watchdog: Run `PYTHONUNBUFFERED=1 timeout 45 python3 {SCRIPTS_DIR}/wolf-monitor.py`. Parse JSON output.\n\nKEY CHECKS:\n1. **Cross-margin buffer** (`crypto_liq_buffer_pct`): If <50% → WARNING to user. If <30% → CRITICAL, consider closing weakest position.\n2. **Position alerts**: Any alert with level=CRITICAL → immediate Telegram alert ({tg}). WARNING → alert if new (don't repeat same warning within 15min).\n3. **Rotation check**: Compare each position's ROE. If any position is -15%+ ROE AND emerging movers show a strong climber (top 10, 3+ reasons) we DON'T hold → suggest rotation to user.\n4. **XYZ isolated liq**: If liq_distance_pct < 15% → alert user.\n5. Save output to /data/workspace/watchdog-last.json for dedup.\n\nIf no alerts needed → HEARTBEAT_OK."
        }
    },
    "portfolio": {
        "name": "WOLF Portfolio (15min)",
        "schedule": {"kind": "every", "everyMs": 900000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"WOLF portfolio update: Get clearinghouse state for wallet {wallet}. Send user a concise Telegram update ({tg}). Code block table format. Include account value and position summary."
        }
    },
    "health_check": {
        "name": "WOLF Job Health Check (10min)",
        "schedule": {"kind": "every", "everyMs": 600000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"WOLF Health Check: Run `PYTHONUNBUFFERED=1 python3 {SCRIPTS_DIR}/job-health-check.py`, parse JSON.\n\nIf any CRITICAL issues → fix immediately (deactivate orphan DSLs, create missing DSLs for unprotected positions, fix direction mismatches). Alert user on Telegram ({tg}) for critical issues.\nIf only WARNINGs → fix silently (deactivate orphans, note stale crons).\nIf no issues → HEARTBEAT_OK."
        }
    },
    "opportunity_scanner": {
        "name": "WOLF Scanner (15min)",
        "schedule": {"kind": "every", "everyMs": 900000},
        "sessionTarget": "main",
        "wakeMode": "now",
        "payload": {
            "kind": "systemEvent",
            "text": f"WOLF scanner: Run `PYTHONUNBUFFERED=1 timeout 180 python3 {SCRIPTS_DIR}/opportunity-scan.py 2>/dev/null`. Read /data/workspace/wolf-strategy.json for rules. Wallet: {wallet} (strategy {strategy_id[:8]}). Max {slots} concurrent positions, ${margin_str} margin each, {default_leverage}x leverage. XYZ positions use leverageType ISOLATED on same wallet. Threshold 175+. Check existing positions before opening. If good opportunity → open position, create DSL state file (dsl-state-WOLF-{{ASSET}}.json), create DSL cron, alert user ({tg}). Otherwise HEARTBEAT_OK. AUTO-DELEVER: If account below ${auto_delever_threshold:,} → max {slots - 1} positions only."
        }
    }
}

print("\n" + "=" * 60)
print("  WOLF v4 Configuration Summary")
print("=" * 60)
print(f"""
  Wallet:           {wallet}
  Strategy ID:      {strategy_id}
  Budget:           ${budget:,.2f}
  Slots:            {slots}
  Margin/Slot:      ${margin_per_slot:,.2f}
  Default Leverage:  {default_leverage}x
  Notional/Slot:    ${notional_per_slot:,.2f}
  Margin Buffer:    ${margin_buffer:,.2f}
  Daily Loss Limit: ${daily_loss_limit:,.2f}
  Drawdown Cap:     ${drawdown_cap:,.2f}
  Auto-Delever:     Below ${auto_delever_threshold:,}
  Telegram:         {tg}
""")

print("=" * 60)
print("  Next Steps: Create 7 cron jobs")
print("=" * 60)
print("""
Use OpenClaw cron to create each job. Example:

  openclaw cron add --json '{
    "name": "WOLF Emerging Movers v3 (60s)",
    "schedule": { "kind": "every", "everyMs": 60000 },
    "sessionTarget": "main",
    "wakeMode": "now",
    "payload": { "kind": "systemEvent", "text": "..." }
  }'

See references/cron-templates.md in the wolf-strategy skill
for the exact payload text for each of the 7 jobs.

DSL crons are created per-position (when the agent opens a trade).
You only need to create the other 6 at setup time.
""")

# Output full result as JSON for programmatic use
result = {
    "config": config,
    "cronTemplates": cron_templates,
    "maxLeverageFile": MAX_LEV_FILE,
    "configFile": CONFIG_FILE,
}
print(json.dumps(result, indent=2))
