#!/usr/bin/env python3
"""
WOLF Strategy Monitor v1
- Checks all positions across both wallets (crypto + XYZ)
- Computes liquidation distance vs DSL floor distance
- Flags positions where liq is closer than DSL
- Checks emerging movers for rotation candidates
- Outputs JSON with alerts array
"""
import subprocess, json, sys, os, time

CRYPTO_WALLET = "0x7df5eaec3ca1d22196ffeed03294d1a5bb32ff6d"
CRYPTO_STRATEGY = "0af20dcc-cc7d-4d72-8483-f7cd1e46572c"
XYZ_WALLET = "0x4c6f377247d28802ca87a97e10d2b98474a79b8e"
XYZ_STRATEGY = "f82981bc-91ba-46ac-87b6-b6326fe38fe7"
DSL_STATE_DIR = "/data/workspace"
EMERGING_HISTORY = "/data/workspace/emerging-movers-history.json"

def mcporter_call(tool, **kwargs):
    args = [f"{k}={v}" for k, v in kwargs.items()]
    cmd = ["mcporter", "call", f"senpi.{tool}"] + args + ["--output", "json"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        d = json.loads(r.stdout)
        if d.get("content"):
            return json.loads(d["content"][0]["text"])
        return d
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_clearinghouse(wallet):
    return mcporter_call("strategy_get_clearinghouse_state", strategy_wallet=wallet)

def get_dsl_state(asset):
    path = os.path.join(DSL_STATE_DIR, f"dsl-state-WOLF-{asset}.json")
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return None

def analyze_positions():
    results = {"positions": [], "alerts": [], "summary": {}}
    
    # Crypto wallet
    ch = get_clearinghouse(CRYPTO_WALLET)
    if not ch.get("success"):
        results["alerts"].append({"level": "ERROR", "msg": "Failed to fetch crypto clearinghouse"})
        return results
    
    main = ch["data"]["main"]
    acct_value = float(main["marginSummary"]["accountValue"])
    total_margin = float(main["marginSummary"]["totalMarginUsed"])
    maint_margin = float(main["crossMaintenanceMarginUsed"])
    
    results["summary"]["crypto_account"] = acct_value
    results["summary"]["crypto_margin_used"] = total_margin
    results["summary"]["crypto_margin_pct"] = round(total_margin / acct_value * 100, 1) if acct_value > 0 else 0
    results["summary"]["crypto_maint_margin"] = maint_margin
    # Cross-margin liquidation: when account value drops below maintenance margin
    # Buffer = (accountValue - maintMargin) / accountValue
    results["summary"]["crypto_liq_buffer_pct"] = round((acct_value - maint_margin) / acct_value * 100, 1) if acct_value > 0 else 0
    
    for ap in main.get("assetPositions", []):
        pos = ap["position"]
        coin = pos["coin"]
        szi = float(pos["szi"])
        if szi == 0:
            continue
        direction = "LONG" if szi > 0 else "SHORT"
        entry = float(pos["entryPx"])
        liq = float(pos["liquidationPx"]) if pos.get("liquidationPx") else None
        upnl = float(pos["unrealizedPnl"])
        roe = float(pos["returnOnEquity"]) * 100
        price = float(pos["positionValue"]) / abs(szi)
        
        # DSL floor
        dsl = get_dsl_state(coin)
        dsl_floor = float(dsl["floorPrice"]) if dsl and dsl.get("active") else None
        
        # Distance calculations
        liq_dist_pct = None
        dsl_dist_pct = None
        if liq and direction == "LONG":
            liq_dist_pct = round((price - liq) / price * 100, 1)
        elif liq and direction == "SHORT":
            liq_dist_pct = round((liq - price) / price * 100, 1)
        
        if dsl_floor and direction == "LONG":
            dsl_dist_pct = round((price - dsl_floor) / price * 100, 1)
        elif dsl_floor and direction == "SHORT":
            dsl_dist_pct = round((dsl_floor - price) / price * 100, 1)
        
        p = {
            "coin": coin, "direction": direction, "entry": entry,
            "price": round(price, 4), "liq": liq, "upnl": round(upnl, 2),
            "roe_pct": round(roe, 2), "liq_distance_pct": liq_dist_pct,
            "dsl_floor": dsl_floor, "dsl_distance_pct": dsl_dist_pct,
            "wallet": "crypto", "margin": round(float(pos["marginUsed"]), 2)
        }
        results["positions"].append(p)
        
        # Alert: liq closer than DSL floor
        if liq_dist_pct is not None and dsl_dist_pct is not None:
            if liq_dist_pct < dsl_dist_pct:
                results["alerts"].append({
                    "level": "CRITICAL",
                    "msg": f"{coin} {direction}: Liquidation ({liq_dist_pct}% away) CLOSER than DSL floor ({dsl_dist_pct}% away)!"
                })
        
        # Alert: ROE below -15%
        if roe < -15:
            results["alerts"].append({
                "level": "WARNING",
                "msg": f"{coin} {direction}: ROE at {round(roe, 1)}% — approaching danger zone"
            })
        
        # Alert: liq distance < 30%
        if liq_dist_pct is not None and liq_dist_pct < 30:
            results["alerts"].append({
                "level": "WARNING",
                "msg": f"{coin} {direction}: Liquidation only {liq_dist_pct}% away"
            })
    
    # Cross-margin alert: if buffer < 30%
    buf = results["summary"]["crypto_liq_buffer_pct"]
    if buf < 30:
        results["alerts"].append({
            "level": "CRITICAL" if buf < 15 else "WARNING",
            "msg": f"Cross-margin buffer: {buf}% (account ${round(acct_value, 2)}, maint margin ${round(maint_margin, 2)})"
        })
    
    # XYZ wallet
    ch2 = get_clearinghouse(XYZ_WALLET)
    if ch2.get("success"):
        xyz = ch2["data"].get("xyz", {})
        xyz_acct = float(xyz.get("marginSummary", {}).get("accountValue", "0"))
        results["summary"]["xyz_account"] = xyz_acct
        for ap in xyz.get("assetPositions", []):
            pos = ap["position"]
            coin = pos["coin"]
            szi = float(pos["szi"])
            if szi == 0:
                continue
            direction = "LONG" if szi > 0 else "SHORT"
            entry = float(pos["entryPx"])
            liq = float(pos["liquidationPx"]) if pos.get("liquidationPx") else None
            upnl = float(pos["unrealizedPnl"])
            roe = float(pos["returnOnEquity"]) * 100
            price = float(pos["positionValue"]) / abs(szi)
            
            liq_dist_pct = None
            if liq and direction == "LONG":
                liq_dist_pct = round((price - liq) / price * 100, 1)
            elif liq and direction == "SHORT":
                liq_dist_pct = round((liq - price) / price * 100, 1)
            
            p = {
                "coin": coin, "direction": direction, "entry": entry,
                "price": round(price, 4), "liq": liq, "upnl": round(upnl, 2),
                "roe_pct": round(roe, 2), "liq_distance_pct": liq_dist_pct,
                "dsl_floor": None, "dsl_distance_pct": None,
                "wallet": "xyz", "margin": round(float(pos["marginUsed"]), 2)
            }
            results["positions"].append(p)
            
            # XYZ isolated — liq distance warning
            if liq_dist_pct is not None and liq_dist_pct < 25:
                results["alerts"].append({
                    "level": "WARNING",
                    "msg": f"{coin} {direction}: Liquidation only {liq_dist_pct}% away (isolated)"
                })
    
    # Check emerging movers for rotation candidates
    try:
        with open(EMERGING_HISTORY) as f:
            history = json.load(f)
        if len(history) >= 2:
            latest = history[-1].get("top_movers", [])
            prev = history[-2].get("top_movers", [])
            # Find assets climbing fast that we DON'T hold
            held_coins = {p["coin"] for p in results["positions"]}
            climbers = []
            for m in latest[:10]:
                asset = m.get("asset", "")
                if asset not in held_coins:
                    # Check if rank improved
                    prev_ranks = {pm.get("asset"): pm.get("rank", 99) for pm in prev}
                    prev_rank = prev_ranks.get(asset, 99)
                    curr_rank = m.get("rank", 99)
                    if curr_rank < prev_rank and curr_rank <= 15:
                        climbers.append(f"{asset} #{prev_rank}→#{curr_rank}")
            if climbers:
                results["alerts"].append({
                    "level": "INFO",
                    "msg": f"Emerging rotation candidates: {', '.join(climbers[:3])}"
                })
    except:
        pass
    
    # Total P&L
    total_upnl = sum(p["upnl"] for p in results["positions"])
    results["summary"]["total_upnl"] = round(total_upnl, 2)
    results["summary"]["total_account"] = round(
        results["summary"].get("crypto_account", 0) + results["summary"].get("xyz_account", 0), 2
    )
    
    return results

if __name__ == "__main__":
    r = analyze_positions()
    print(json.dumps(r, indent=2))
