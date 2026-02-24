#!/usr/bin/env python3
"""
Smart Money Flip Detector — Lightweight (1 API call)
Checks if SM direction has flipped against any active AUTO positions.
Runs every 5 min. Outputs JSON with alerts.

Usage: python3 sm-flip-check.py
Reads active DSL state files to know current positions.
"""

import json, subprocess, sys, os, glob
from datetime import datetime, timezone

AUTO_WALLET = "0x07a94ad0b01cc6d70c8c85afcc1b26e576b38857"
STATE_DIR = "/data/workspace"
STATE_PATTERN = "dsl-state-WOLF-*.json"

def get_active_positions():
    """Read all active AUTO DSL state files."""
    positions = []
    for f in glob.glob(os.path.join(STATE_DIR, STATE_PATTERN)):
        try:
            with open(f) as fh:
                state = json.load(fh)
            if state.get("active"):
                positions.append({
                    "asset": state["asset"],
                    "direction": state["direction"],
                    "file": f
                })
        except:
            continue
    return positions

def get_sm_data():
    """Fetch smart money data via leaderboard_get_markets."""
    result = subprocess.run(
        ["mcporter", "call", "senpi", "leaderboard_get_markets", "--args", "{}"],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(result.stdout)

def analyze(positions, sm_data):
    """Check for SM flips against our positions."""
    alerts = []
    
    # Parse SM data — find per-asset dominant direction
    # Structure: data.markets.markets[] (array of {token, direction, pct_of_top_traders_gain, trader_count, ...})
    raw = sm_data.get("data", sm_data.get("result", {}))
    if isinstance(raw, dict):
        inner = raw.get("markets", raw)
        if isinstance(inner, dict):
            markets = inner.get("markets", [])
        elif isinstance(inner, list):
            markets = inner
        else:
            markets = []
    else:
        markets = []
    if not isinstance(markets, list):
        return {"error": "unexpected SM data format", "raw_keys": str(type(markets))}
    
    # Build asset→SM map (keep dominant side by pnl%)
    sm_map = {}
    for m in markets:
        asset = m.get("token") or m.get("asset") or m.get("coin", "")
        if not asset:
            continue
        pnl_pct = float(m.get("pct_of_top_traders_gain", m.get("pnlContribution", 0)) or 0) * 100  # convert to %
        traders = int(m.get("trader_count", m.get("traderCount", 0)) or 0)
        direction = (m.get("direction") or "").upper()
        
        # Get freshness signals (may not be in this endpoint — default safe)
        avg_at_peak = float(m.get("avgAtPeak", 50) or 50)
        near_peak_pct = float(m.get("nearPeakPct", 0) or 0)
        
        key = asset.upper()
        if key not in sm_map or abs(pnl_pct) > abs(sm_map[key].get("pnlPct", 0)):
            sm_map[key] = {
                "direction": direction,
                "pnlPct": pnl_pct,
                "traders": traders,
                "avgAtPeak": avg_at_peak,
                "nearPeakPct": near_peak_pct
            }
    
    for pos in positions:
        asset = pos["asset"].upper()
        sm = sm_map.get(asset)
        if not sm:
            continue
        
        my_dir = pos["direction"].upper()
        sm_dir = sm["direction"]
        
        # Check for flip
        flipped = (my_dir == "LONG" and sm_dir == "SHORT") or \
                  (my_dir == "SHORT" and sm_dir == "LONG")
        
        # Conviction scoring
        conviction = 0
        if sm["pnlPct"] > 5: conviction += 2
        elif sm["pnlPct"] > 1: conviction += 1
        if sm["traders"] > 100: conviction += 2
        elif sm["traders"] > 30: conviction += 1
        if sm["nearPeakPct"] > 50: conviction += 2
        elif sm["nearPeakPct"] > 20: conviction += 1
        if sm["avgAtPeak"] > 80: conviction += 1
        
        alert_level = "none"
        if flipped and conviction >= 4:
            alert_level = "FLIP_NOW"
        elif flipped and conviction >= 2:
            alert_level = "FLIP_WARNING"
        elif flipped:
            alert_level = "WATCH"
        
        alerts.append({
            "asset": asset,
            "myDirection": my_dir,
            "smDirection": sm_dir,
            "flipped": flipped,
            "alertLevel": alert_level,
            "conviction": conviction,
            "smPnlPct": sm["pnlPct"],
            "smTraders": sm["traders"],
            "avgAtPeak": sm["avgAtPeak"],
            "nearPeakPct": sm["nearPeakPct"]
        })
    
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "positions": len(positions),
        "alerts": alerts,
        "hasFlipSignal": any(a["alertLevel"] in ("FLIP_NOW", "FLIP_WARNING") for a in alerts)
    }

if __name__ == "__main__":
    positions = get_active_positions()
    if not positions:
        print(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "positions": 0, "alerts": [], "hasFlipSignal": False}))
        sys.exit(0)
    
    sm_data = get_sm_data()
    result = analyze(positions, sm_data)
    print(json.dumps(result))
