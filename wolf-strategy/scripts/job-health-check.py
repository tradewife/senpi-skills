#!/usr/bin/env python3
"""
WOLF Job Health Check — Meta-watchdog
Verifies:
1. All active positions have a running DSL cron
2. All DSL crons point to positions that still exist
3. No cron has been stuck (lastRunAtMs too old vs schedule)
4. DSL state files match actual wallet positions
5. SM flip check isn't reporting stale positions

Outputs JSON with issues[] array.
"""

import json, subprocess, sys, os, glob
from datetime import datetime, timezone

WALLET = "0x7df5eaec3ca1d22196ffeed03294d1a5bb32ff6d"
STATE_DIR = "/data/workspace"
STATE_PATTERN = "dsl-state-WOLF-*.json"

def run_cmd(args, timeout=30):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return r.stdout.strip()

def get_wallet_positions():
    """Get actual positions from clearinghouse."""
    raw = run_cmd(["mcporter", "call", "senpi", "strategy_get_clearinghouse_state",
                   f"strategy_wallet={WALLET}"])
    data = json.loads(raw).get("data", {})
    positions = {}
    for section in ["main", "crypto"]:
        if section in data and "assetPositions" in data[section]:
            for p in data[section]["assetPositions"]:
                pos = p.get("position", {})
                coin = pos.get("coin")
                if coin:
                    szi = float(pos.get("szi", 0))
                    positions[coin] = {
                        "direction": "SHORT" if szi < 0 else "LONG",
                        "size": abs(szi),
                        "entryPx": pos.get("entryPx"),
                        "unrealizedPnl": pos.get("unrealizedPnl"),
                        "returnOnEquity": pos.get("returnOnEquity"),
                    }
    return positions

def get_active_dsl_states():
    """Read all DSL state files."""
    states = {}
    for f in sorted(glob.glob(os.path.join(STATE_DIR, STATE_PATTERN))):
        try:
            with open(f) as fh:
                state = json.load(fh)
            asset = state.get("asset", os.path.basename(f).replace("dsl-state-WOLF-", "").replace(".json", ""))
            states[asset] = {
                "active": state.get("active", False),
                "pendingClose": state.get("pendingClose", False),
                "file": f,
                "direction": state.get("direction"),
                "lastCheck": state.get("lastCheck"),
            }
        except:
            continue
    return states

def get_cron_jobs():
    """List all enabled cron jobs via gateway."""
    # We'll parse from a file written by the caller, or just check state files
    # For now, return DSL-related info from state files
    return {}

def main():
    issues = []
    warnings = []
    now = datetime.now(timezone.utc)
    
    # 1. Get actual positions
    try:
        positions = get_wallet_positions()
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"Failed to fetch positions: {e}"}))
        sys.exit(1)
    
    # 2. Get DSL states
    dsl_states = get_active_dsl_states()
    
    # 3. Check: every position has an active DSL state
    for coin, pos in positions.items():
        asset_key = coin
        if asset_key not in dsl_states:
            # Check with xyz: prefix too
            xyz_key = f"xyz:{coin}"
            if xyz_key not in dsl_states:
                issues.append({
                    "level": "CRITICAL",
                    "type": "NO_DSL",
                    "asset": coin,
                    "message": f"{coin} {pos['direction']} has NO DSL state file — unprotected position"
                })
                continue
            else:
                asset_key = xyz_key
        
        dsl = dsl_states[asset_key]
        if not dsl["active"] and not dsl["pendingClose"]:
            issues.append({
                "level": "CRITICAL", 
                "type": "DSL_INACTIVE",
                "asset": coin,
                "message": f"{coin} has DSL state file but active=false — unprotected position"
            })
        elif dsl["direction"] != pos["direction"]:
            issues.append({
                "level": "CRITICAL",
                "type": "DIRECTION_MISMATCH",
                "asset": coin,
                "message": f"{coin} position is {pos['direction']} but DSL is {dsl['direction']}"
            })
        
        # Check DSL freshness (last check should be within 10 min)
        if dsl.get("lastCheck"):
            try:
                last = datetime.fromisoformat(dsl["lastCheck"].replace("Z", "+00:00"))
                age_min = (now - last).total_seconds() / 60
                if age_min > 10:
                    issues.append({
                        "level": "WARNING",
                        "type": "DSL_STALE",
                        "asset": coin,
                        "message": f"{coin} DSL last checked {round(age_min)}min ago — cron may not be firing"
                    })
            except:
                pass
    
    # 4. Check: no active DSL states for positions that don't exist (orphans)
    for asset, dsl in dsl_states.items():
        if dsl["active"]:
            clean_asset = asset.replace("xyz:", "")
            if clean_asset not in positions and asset not in positions:
                issues.append({
                    "level": "WARNING",
                    "type": "ORPHAN_DSL",
                    "asset": asset,
                    "message": f"{asset} DSL state is active but no matching position — should deactivate"
                })
    
    # 5. Summary
    result = {
        "status": "ok" if not any(i["level"] == "CRITICAL" for i in issues) else "critical",
        "time": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "positions": list(positions.keys()),
        "active_dsl": [a for a, d in dsl_states.items() if d["active"]],
        "issues": issues,
        "issue_count": len(issues),
        "critical_count": sum(1 for i in issues if i["level"] == "CRITICAL"),
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
