#!/usr/bin/env python3
"""
Opportunity Scanner — 3-stage funnel, 4-pillar scoring
Scans all 521 Hyperliquid perps, outputs compact JSON for LLM formatting.
Token cost: ~0 (all computation in Python).
"""

import json
import sys
import subprocess
import time
import math
from datetime import datetime, timezone

# ─── Config ───
TOP_N_DEEP = 15          # How many assets get full candle analysis
CANDLE_INTERVAL = "1h"
CANDLE_HOURS = 24
MIN_VOLUME_24H = 500_000  # $500k minimum daily volume for Stage 1

# ─── Pillar weights (equal by default) ───
W_SMART_MONEY = 0.25
W_MARKET_STRUCTURE = 0.25
W_TECHNICALS = 0.25
W_FUNDING = 0.25

# ─── Helpers ───

def fetch_json(payload):
    """Fetch from Hyperliquid info API."""
    r = subprocess.run(
        ["curl", "-s", "https://api.hyperliquid.xyz/info",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True, timeout=30
    )
    return json.loads(r.stdout)

def fetch_mcporter(tool, args=""):
    """Call mcporter tool, return parsed JSON. Writes to temp file to avoid pipe issues with large output."""
    import tempfile
    tmp = tempfile.mktemp(suffix=".json")
    cmd = f"mcporter call senpi.{tool} --output json {args} > {tmp} 2>/dev/null"
    subprocess.run(cmd, shell=True, timeout=60)
    with open(tmp) as f:
        data = json.load(f)
    import os; os.unlink(tmp)
    return data

def calc_rsi(closes, period=14):
    """RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i-1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_ema(values, period):
    """Exponential moving average."""
    if not values:
        return []
    ema = [values[0]]
    k = 2 / (period + 1)
    for v in values[1:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema

def volume_ratio(candles, recent_n=4):
    """Ratio of recent volume vs prior period average."""
    if len(candles) < 6:
        return 1.0
    recent = candles[-recent_n:]
    prior = candles[:-recent_n]
    if not prior:
        return 1.0
    recent_avg = sum(float(c["v"]) for c in recent) / len(recent)
    prior_avg = sum(float(c["v"]) for c in prior) / len(prior)
    if prior_avg == 0:
        return 1.0
    return round(recent_avg / prior_avg, 2)

def price_changes(candles):
    """Calculate 1h, 4h, 24h price changes."""
    if not candles:
        return {"chg1h": 0, "chg4h": 0, "chg24h": 0}
    current = float(candles[-1]["c"])
    def pct(idx):
        if abs(idx) > len(candles):
            idx = -len(candles)
        ref = float(candles[idx]["o"])
        return round((current - ref) / ref * 100, 2) if ref else 0
    return {
        "chg1h": pct(-1),
        "chg4h": pct(-4) if len(candles) >= 4 else pct(-len(candles)),
        "chg24h": pct(0)
    }

def find_swing_levels(candles, lookback=5):
    """Find recent swing highs and lows for S/R."""
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]
    swing_highs = []
    swing_lows = []
    for i in range(lookback, len(candles) - lookback):
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            swing_highs.append(highs[i])
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            swing_lows.append(lows[i])
    return swing_highs[-3:] if swing_highs else [], swing_lows[-3:] if swing_lows else []

def detect_patterns(candles):
    """Detect candlestick patterns from recent candles. Returns list of pattern names."""
    if len(candles) < 3:
        return []
    patterns = []
    
    # Last 3 candles
    c1 = candles[-3]  # oldest
    c2 = candles[-2]
    c3 = candles[-1]  # newest
    
    def body(c):
        return abs(float(c["c"]) - float(c["o"]))
    def full_range(c):
        return float(c["h"]) - float(c["l"])
    def is_bullish(c):
        return float(c["c"]) > float(c["o"])
    def upper_wick(c):
        return float(c["h"]) - max(float(c["c"]), float(c["o"]))
    def lower_wick(c):
        return min(float(c["c"]), float(c["o"])) - float(c["l"])
    
    fr3 = full_range(c3)
    b3 = body(c3)
    
    if fr3 > 0:
        # Pin bar / hammer (long lower wick, small body at top)
        if lower_wick(c3) > b3 * 2 and upper_wick(c3) < b3 * 0.5 and fr3 > 0:
            patterns.append("hammer" if is_bullish(c3) else "inverted_hammer")
        
        # Shooting star (long upper wick, small body at bottom)
        if upper_wick(c3) > b3 * 2 and lower_wick(c3) < b3 * 0.5:
            patterns.append("shooting_star")
        
        # Doji (tiny body relative to range)
        if b3 < fr3 * 0.1 and fr3 > 0:
            patterns.append("doji")
    
    # Bullish engulfing
    if not is_bullish(c2) and is_bullish(c3):
        if float(c3["c"]) > float(c2["o"]) and float(c3["o"]) < float(c2["c"]):
            patterns.append("bullish_engulfing")
    
    # Bearish engulfing
    if is_bullish(c2) and not is_bullish(c3):
        if float(c3["c"]) < float(c2["o"]) and float(c3["o"]) > float(c2["c"]):
            patterns.append("bearish_engulfing")
    
    # Three soldiers (3 consecutive bullish with higher closes)
    if is_bullish(c1) and is_bullish(c2) and is_bullish(c3):
        if float(c3["c"]) > float(c2["c"]) > float(c1["c"]):
            patterns.append("three_soldiers")
    
    # Three crows (3 consecutive bearish with lower closes)
    if not is_bullish(c1) and not is_bullish(c2) and not is_bullish(c3):
        if float(c3["c"]) < float(c2["c"]) < float(c1["c"]):
            patterns.append("three_crows")
    
    return patterns

def analyze_trend(candles_4h):
    """Analyze higher timeframe trend from 4h candles. Returns trend direction and strength."""
    if len(candles_4h) < 5:
        return "neutral", 0
    
    closes = [float(c["c"]) for c in candles_4h]
    
    # EMA 5 vs EMA 13 on 4h (like 20/52 on 1h)
    ema_fast = calc_ema(closes, 5)
    ema_slow = calc_ema(closes, 13)
    
    if not ema_fast or not ema_slow:
        return "neutral", 0
    
    # Current EMA relationship
    fast_now = ema_fast[-1]
    slow_now = ema_slow[-1]
    price_now = closes[-1]
    
    # Trend direction
    if fast_now > slow_now and price_now > fast_now:
        trend = "strong_up"
        strength = min(100, int((fast_now - slow_now) / slow_now * 1000))
    elif fast_now > slow_now:
        trend = "up"
        strength = min(70, int((fast_now - slow_now) / slow_now * 500))
    elif fast_now < slow_now and price_now < fast_now:
        trend = "strong_down"
        strength = min(100, int((slow_now - fast_now) / slow_now * 1000))
    elif fast_now < slow_now:
        trend = "down"
        strength = min(70, int((slow_now - fast_now) / slow_now * 500))
    else:
        trend = "neutral"
        strength = 0
    
    # Check if EMAs are converging or diverging
    if len(ema_fast) >= 3 and len(ema_slow) >= 3:
        gap_now = abs(ema_fast[-1] - ema_slow[-1])
        gap_prev = abs(ema_fast[-3] - ema_slow[-3])
        if gap_now > gap_prev:
            strength = min(100, strength + 15)  # diverging = strengthening
    
    return trend, strength

def multi_tf_analysis(candles_1h, candles_15m, candles_4h):
    """Complete multi-timeframe technical analysis."""
    result = {}
    
    # 4h trend (higher TF context)
    trend_4h, trend_strength = analyze_trend(candles_4h)
    result["trend4h"] = trend_4h
    result["trendStrength"] = trend_strength
    
    # 1h RSI + volume (setup timeframe)
    closes_1h = [float(c["c"]) for c in candles_1h]
    result["rsi1h"] = calc_rsi(closes_1h)
    result["volRatio1h"] = volume_ratio(candles_1h, 4)
    result.update(price_changes(candles_1h))
    
    # 1h swing levels
    swing_highs, swing_lows = find_swing_levels(candles_1h, 3)
    result["resistance"] = round(max(swing_highs), 4) if swing_highs else None
    result["support"] = round(min(swing_lows), 4) if swing_lows else None
    
    # 15m analysis (entry timeframe)
    if candles_15m:
        closes_15m = [float(c["c"]) for c in candles_15m]
        result["rsi15m"] = calc_rsi(closes_15m)
        result["volRatio15m"] = volume_ratio(candles_15m, 4)  # last 1h vs prior 3h
        
        # 15m patterns
        result["patterns15m"] = detect_patterns(candles_15m)
        
        # 15m momentum (last 4 candles = 1h)
        if len(candles_15m) >= 4:
            recent_close = float(candles_15m[-1]["c"])
            hour_ago_open = float(candles_15m[-4]["o"])
            result["momentum15m"] = round((recent_close - hour_ago_open) / hour_ago_open * 100, 3)
        else:
            result["momentum15m"] = 0
        
        # Volume-price divergence on 15m (price dropping but volume surging = reversal signal)
        if len(candles_15m) >= 8:
            recent_vol = sum(float(c["v"]) for c in candles_15m[-4:])
            prior_vol = sum(float(c["v"]) for c in candles_15m[-8:-4])
            recent_chg = float(candles_15m[-1]["c"]) - float(candles_15m[-4]["c"])
            if prior_vol > 0:
                vol_surge = recent_vol / prior_vol
                # Volume up but price down = potential reversal up (and vice versa)
                if vol_surge > 1.5 and recent_chg < 0:
                    result["divergence"] = "bullish"  # selling exhaustion
                elif vol_surge > 1.5 and recent_chg > 0:
                    result["divergence"] = "bearish"  # buying exhaustion
                else:
                    result["divergence"] = None
            else:
                result["divergence"] = None
        else:
            result["divergence"] = None
    else:
        result["rsi15m"] = 50
        result["volRatio15m"] = 1.0
        result["patterns15m"] = []
        result["momentum15m"] = 0
        result["divergence"] = None
    
    # 1h patterns too
    result["patterns1h"] = detect_patterns(candles_1h)
    
    return result

# ─── Scoring functions (each returns 0-100) ───

def score_smart_money(asset_data):
    """Pillar 1: Smart money flow."""
    if not asset_data:
        return 0, "LONG", {}
    pnl_pct = abs(asset_data.get("pnlContributionPct", 0))
    traders = asset_data.get("traderCount", 0)
    accel = asset_data.get("contributionChange4h", 0)
    direction = asset_data.get("dominantDirection", "LONG")
    
    score = 0
    # pnl contribution is the strongest signal — scale aggressively
    if pnl_pct > 15:
        score += 50
    elif pnl_pct > 5:
        score += 35
    elif pnl_pct > 1:
        score += 20
    elif pnl_pct > 0.3:
        score += 10
    
    # Trader count = consensus
    if traders > 300:
        score += 25
    elif traders > 100:
        score += 18
    elif traders > 30:
        score += 10
    elif traders > 10:
        score += 5
    
    # Acceleration (4h contribution change) = fresh momentum
    if abs(accel) > 10:
        score += 20
    elif abs(accel) > 3:
        score += 12
    elif abs(accel) > 1:
        score += 6
    
    # Freshness: are traders still near their 4h peak? (move still running vs already played out)
    avg_at_peak = asset_data.get("avgAtPeak", 50)  # default 50% if no data
    near_peak_pct = asset_data.get("nearPeakPct", 0)
    
    if avg_at_peak > 85:
        score += 15  # move is live, traders at highs
    elif avg_at_peak > 70:
        score += 8   # moderately fresh
    elif avg_at_peak < 50:
        score -= 10  # move is stale, traders gave back gains
    
    if near_peak_pct > 50:
        score += 10  # many traders still at peak = strong momentum
    
    details = {
        "pnlPct": round(pnl_pct, 1),
        "traders": traders,
        "accel": round(accel, 1),
        "direction": direction,
        "avgAtPeak": avg_at_peak,
        "nearPeakPct": near_peak_pct
    }
    return min(100, round(score)), direction, details

def score_market_structure(meta):
    """Pillar 2: Volume, OI, market dynamics."""
    vol24h = meta.get("volume24h", 0)
    oi = meta.get("openInterest", 0)
    prev_day_vol = meta.get("prevDayVolume", vol24h)
    
    score = 0
    # Volume magnitude
    if vol24h > 50_000_000:
        score += 30
    elif vol24h > 10_000_000:
        score += 20
    elif vol24h > 1_000_000:
        score += 10
    
    # Volume trend (vs previous day)
    if prev_day_vol > 0:
        vol_change = vol24h / prev_day_vol
        if vol_change > 2.0:
            score += 30  # volume surge
        elif vol_change > 1.3:
            score += 20
        elif vol_change > 1.0:
            score += 10
    
    # OI significance
    if oi > 10_000_000:
        score += 20
    elif oi > 1_000_000:
        score += 10
    
    # OI to volume ratio (high OI relative to vol = building positions)
    if vol24h > 0:
        oi_vol = oi / vol24h
        if 0.3 < oi_vol < 3.0:
            score += 20  # healthy ratio
    
    details = {
        "vol24h": round(vol24h),
        "oi": round(oi),
        "volTrend": round(vol24h / prev_day_vol, 2) if prev_day_vol > 0 else 1.0
    }
    return min(100, round(score)), details

def score_technicals(tf_data, direction):
    """Pillar 3: Multi-timeframe technicals scoring."""
    score = 0
    
    rsi1h = tf_data.get("rsi1h", 50)
    rsi15m = tf_data.get("rsi15m", 50)
    vol1h = tf_data.get("volRatio1h", 1.0)
    vol15m = tf_data.get("volRatio15m", 1.0)
    trend = tf_data.get("trend4h", "neutral")
    trend_str = tf_data.get("trendStrength", 0)
    patterns15m = tf_data.get("patterns15m", [])
    patterns1h = tf_data.get("patterns1h", [])
    momentum15m = tf_data.get("momentum15m", 0)
    divergence = tf_data.get("divergence")
    chg4h = tf_data.get("chg4h", 0)
    chg1h = tf_data.get("chg1h", 0)
    
    # ── 4H Trend alignment (0-20 pts) ──
    if direction == "LONG":
        if trend in ("strong_up", "up"):
            score += 20
        elif trend == "neutral":
            score += 5
        elif trend in ("strong_down", "down"):
            score -= 5  # counter-trend trade
    else:
        if trend in ("strong_down", "down"):
            score += 20
        elif trend == "neutral":
            score += 5
        elif trend in ("strong_up", "up"):
            score -= 5
    
    # ── 1H RSI (0-20 pts) ──
    if direction == "LONG":
        if rsi1h < 30: score += 20
        elif rsi1h < 40: score += 15
        elif rsi1h < 55: score += 8
        elif rsi1h > 70: score -= 10
    else:
        if rsi1h > 70: score += 20
        elif rsi1h > 60: score += 15
        elif rsi1h > 45: score += 8
        elif rsi1h < 30: score -= 10
    
    # ── 15M RSI convergence (0-10 pts) ──
    # If 15m RSI aligns with 1h RSI direction = stronger signal
    if direction == "LONG":
        if rsi15m < 35 and rsi1h < 45:
            score += 10  # both oversold = strong
        elif rsi15m < 40:
            score += 5
    else:
        if rsi15m > 65 and rsi1h > 55:
            score += 10
        elif rsi15m > 60:
            score += 5
    
    # ── Volume confirmation (0-15 pts) ──
    # Use best of 1h and 15m volume signals
    best_vol = max(vol1h, vol15m)
    if best_vol > 2.0:
        score += 15
    elif best_vol > 1.5:
        score += 10
    elif best_vol > 1.2:
        score += 5
    elif best_vol < 0.5:
        score -= 5  # dying volume
    
    # ── 15M Candlestick patterns (0-15 pts) ──
    bullish_patterns = {"hammer", "bullish_engulfing", "three_soldiers", "doji"}
    bearish_patterns = {"shooting_star", "bearish_engulfing", "three_crows", "doji"}
    
    relevant_patterns = bullish_patterns if direction == "LONG" else bearish_patterns
    found = set(patterns15m) & relevant_patterns
    if found:
        score += min(15, len(found) * 8)
    
    # 1h patterns (weaker signal but adds confirmation)
    found_1h = set(patterns1h) & relevant_patterns
    if found_1h:
        score += min(5, len(found_1h) * 3)
    
    # ── Momentum alignment (0-10 pts) ──
    if direction == "LONG" and momentum15m > 0.1:
        score += 10
    elif direction == "LONG" and momentum15m < -0.3:
        score += 5  # dip entry
    elif direction == "SHORT" and momentum15m < -0.1:
        score += 10
    elif direction == "SHORT" and momentum15m > 0.3:
        score += 5  # bounce entry
    
    # ── 4h momentum (0-10 pts) ──
    if direction == "LONG" and chg4h > 1:
        score += 10
    elif direction == "LONG" and chg4h < -2:
        score += 7  # dip buy
    elif direction == "SHORT" and chg4h < -1:
        score += 10
    elif direction == "SHORT" and chg4h > 2:
        score += 7  # bounce short
    
    # ── Volume-price divergence (0-10 pts) ──
    if divergence == "bullish" and direction == "LONG":
        score += 10  # selling exhaustion, good for longs
    elif divergence == "bearish" and direction == "SHORT":
        score += 10  # buying exhaustion, good for shorts
    elif divergence == "bullish" and direction == "SHORT":
        score -= 5  # divergence against us
    elif divergence == "bearish" and direction == "LONG":
        score -= 5
    
    # Build details
    details = {
        "rsi1h": rsi1h,
        "rsi15m": rsi15m,
        "volRatio1h": vol1h,
        "volRatio15m": vol15m,
        "trend4h": trend,
        "trendStrength": trend_str,
        "patterns15m": patterns15m,
        "patterns1h": patterns1h,
        "momentum15m": momentum15m,
        "divergence": divergence,
        "chg1h": tf_data.get("chg1h", 0),
        "chg4h": tf_data.get("chg4h", 0),
        "chg24h": tf_data.get("chg24h", 0),
        "support": tf_data.get("support"),
        "resistance": tf_data.get("resistance"),
    }
    return max(0, min(100, round(score))), details

def score_funding(funding_rate, direction):
    """Pillar 4: Funding rate analysis."""
    score = 0
    ann_rate = funding_rate * 24 * 365 * 100  # annualized %
    favorable = (direction == "LONG" and funding_rate <= 0) or \
                (direction == "SHORT" and funding_rate >= 0)
    
    # Neutral funding = fine, cheap to hold either way
    if abs(ann_rate) < 5:
        score += 40
    elif abs(ann_rate) < 15:
        score += 25 if favorable else 15
    
    # Favorable funding (you get paid)
    if favorable:
        if abs(ann_rate) > 50:
            score += 35  # extreme = crowded other side, you earn carry
        elif abs(ann_rate) > 15:
            score += 25
        elif abs(ann_rate) > 5:
            score += 15
    else:
        # Unfavorable — you pay, but mild is ok
        if abs(ann_rate) > 50:
            score -= 20  # expensive to hold
        elif abs(ann_rate) > 15:
            score -= 10
    
    details = {
        "rate": round(funding_rate * 100, 4),
        "annualized": round(ann_rate, 1),
        "favorable": favorable
    }
    return max(0, min(100, round(score))), details

def suggest_leverage(final_score, direction, rsi, funding_favorable):
    """Suggest leverage based on conviction level."""
    base = 3
    if final_score > 350:
        base = 10
    elif final_score > 280:
        base = 7
    elif final_score > 200:
        base = 5
    
    # Reduce for risky RSI
    if direction == "LONG" and rsi > 65:
        base = max(2, base - 2)
    elif direction == "SHORT" and rsi < 35:
        base = max(2, base - 2)
    
    # Bump slightly if funding favorable
    if funding_favorable and base < 10:
        base += 1
    
    return min(10, base)

# ═══════════════════════════════════════════
# STAGE 1: Bulk screen (all assets)
# ═══════════════════════════════════════════

print("Stage 1: Fetching market structure for all assets...", file=sys.stderr)
meta_raw = fetch_json({"type": "metaAndAssetCtxs"})
meta_info = meta_raw[0]["universe"]  # asset metadata
meta_ctx = meta_raw[1]               # asset contexts (funding, volume, etc.)

assets = {}
for i, (info, ctx) in enumerate(zip(meta_info, meta_ctx)):
    name = info["name"]
    try:
        funding = float(ctx.get("funding", 0))
        vol24h = float(ctx.get("dayNtlVlm", 0))
        oi = float(ctx.get("openInterest", 0))
        mark = float(ctx.get("markPx", 0))
        prev_vol = float(ctx.get("prevDayPx", mark))  # approximate
    except (ValueError, TypeError):
        continue
    
    if vol24h < MIN_VOLUME_24H:
        continue
    
    assets[name] = {
        "funding": funding,
        "volume24h": vol24h,
        "openInterest": oi,
        "markPrice": mark,
        "prevDayVolume": vol24h,  # metaAndAssetCtxs doesn't give prev vol separately
    }

print(f"Stage 1: {len(assets)} assets pass volume filter (of {len(meta_info)} total)", file=sys.stderr)

# ═══════════════════════════════════════════
# STAGE 2: Smart money overlay
# ═══════════════════════════════════════════

print("Stage 2: Fetching smart money data (leaderboard_get_markets)...", file=sys.stderr)
try:
    momentum_raw = fetch_mcporter("leaderboard_get_markets")
    markets_list = momentum_raw.get("data", {}).get("markets", {}).get("markets", [])
    
    sm_by_asset = {}
    for item in markets_list:
        name = item.get("token", "")
        if name not in assets:
            continue
        pnl = float(item.get("pct_of_top_traders_gain", 0)) * 100
        accel = item.get("contribution_pct_change_4h")
        entry = {
            "pnlContributionPct": pnl,
            "traderCount": int(item.get("trader_count", 0)),
            "contributionChange4h": float(accel) if accel is not None else 0.0,
            "dominantDirection": item.get("direction", "long").upper()
        }
        # Keep the direction with higher pnl contribution (dominant side)
        if name not in sm_by_asset or pnl > sm_by_asset[name]["pnlContributionPct"]:
            sm_by_asset[name] = entry
    
    print(f"Stage 2: Smart money data for {len(sm_by_asset)} assets", file=sys.stderr)
    
    # Fetch top traders for "freshness" / at-peak analysis
    print("Stage 2b: Fetching top trader peak data...", file=sys.stderr)
    try:
        top_traders_raw = fetch_mcporter("leaderboard_get_top", "-p limit=100")
        top_traders = top_traders_raw.get("data", {}).get("leaderboard", {}).get("data", [])
        
        from collections import defaultdict
        market_peaks = defaultdict(list)
        for t in top_traders:
            upnl = t.get("unrealized_pnl", 0)
            ath = t.get("ath_delta", 0)
            ratio = upnl / ath if ath > 0 else 0
            for m in t.get("top_markets", []):
                market_peaks[m].append(ratio)
        
        # Enrich sm_by_asset with freshness
        for name in sm_by_asset:
            if name in market_peaks:
                ratios = market_peaks[name]
                avg_at_peak = sum(ratios) / len(ratios)
                near_peak_pct = sum(1 for r in ratios if r > 0.85) / len(ratios)
                sm_by_asset[name]["avgAtPeak"] = round(avg_at_peak * 100, 1)
                sm_by_asset[name]["nearPeakPct"] = round(near_peak_pct * 100, 1)
                sm_by_asset[name]["topTraderCount"] = len(ratios)
        
        print(f"Stage 2b: Peak data for {len(market_peaks)} markets from {len(top_traders)} traders", file=sys.stderr)
    except Exception as e:
        print(f"Stage 2b: Peak data fetch failed ({e}), continuing without", file=sys.stderr)
    
    print(f"Stage 2: Smart money data for {len(sm_by_asset)} assets", file=sys.stderr)
except Exception as e:
    print(f"Stage 2: Smart money fetch failed ({e}), continuing without", file=sys.stderr)
    sm_by_asset = {}

# Quick score all assets and pick top N
quick_scores = []
for name, meta in assets.items():
    sm = sm_by_asset.get(name, {})
    sm_score, direction, _ = score_smart_money(sm)
    
    # If no smart money direction, infer from funding (negative = crowded short, favor long)
    if not sm:
        direction = "LONG" if meta["funding"] < 0 else "SHORT"
    
    ms_score, _ = score_market_structure(meta)
    fund_score, _ = score_funding(meta["funding"], direction)
    
    # Quick composite (no technicals yet)
    quick = (sm_score * W_SMART_MONEY + ms_score * W_MARKET_STRUCTURE + fund_score * W_FUNDING) / (1 - W_TECHNICALS)
    quick_scores.append((name, quick, direction))

# Always include top smart money assets (they must get deep analysis)
sm_top = sorted(sm_by_asset.items(), key=lambda x: x[1]["pnlContributionPct"], reverse=True)
forced_assets = set(name for name, _ in sm_top[:8] if name in assets)

quick_scores.sort(key=lambda x: x[1], reverse=True)
# Take top by score but ensure forced assets are included
top_names = set()
top_assets = []
for item in quick_scores:
    if len(top_assets) >= TOP_N_DEEP and item[0] not in forced_assets:
        continue
    if item[0] not in top_names:
        top_assets.append(item)
        top_names.add(item[0])
    if len(top_names) >= TOP_N_DEEP + len(forced_assets):
        break

print(f"Stage 2: Top {len(top_assets)} for deep analysis: {[a[0] for a in top_assets]}", file=sys.stderr)

# ═══════════════════════════════════════════
# STAGE 3: Deep dive (candles for top N)
# ═══════════════════════════════════════════

print("Stage 3: Fetching multi-TF candles for top assets (4h + 1h + 15m)...", file=sys.stderr)
now_ms = int(time.time() * 1000)

results = []
for name, quick, direction in top_assets:
    try:
        # Fetch 3 timeframes
        # 4h: 7 days = 42 candles (trend context)
        candles_4h = fetch_json({
            "type": "candleSnapshot",
            "req": {"coin": name, "interval": "4h", "startTime": now_ms - (7 * 24 * 3600 * 1000), "endTime": now_ms}
        })
        
        # 1h: 24h = 24 candles (setup)
        candles_1h = fetch_json({
            "type": "candleSnapshot",
            "req": {"coin": name, "interval": "1h", "startTime": now_ms - (24 * 3600 * 1000), "endTime": now_ms}
        })
        
        # 15m: 6h = 24 candles (entry timing + patterns)
        candles_15m = fetch_json({
            "type": "candleSnapshot",
            "req": {"coin": name, "interval": "15m", "startTime": now_ms - (6 * 3600 * 1000), "endTime": now_ms}
        })
        
        if not candles_1h:
            continue
        
        # Multi-timeframe analysis
        tf_data = multi_tf_analysis(candles_1h, candles_15m, candles_4h)
        
        # Full 4-pillar scoring
        sm = sm_by_asset.get(name, {})
        sm_score, _, sm_details = score_smart_money(sm)
        ms_score, ms_details = score_market_structure(assets[name])
        tech_score, tech_details = score_technicals(tf_data, direction)
        fund_score, fund_details = score_funding(assets[name]["funding"], direction)
        
        # Weighted final score (0-400 scale)
        final = round(
            sm_score * W_SMART_MONEY * 4 +
            ms_score * W_MARKET_STRUCTURE * 4 +
            tech_score * W_TECHNICALS * 4 +
            fund_score * W_FUNDING * 4
        )
        
        rsi1h = tech_details.get("rsi1h", 50)
        lev = suggest_leverage(final, direction, rsi1h, fund_details["favorable"])
        
        # Risk flags
        risks = []
        if direction == "LONG" and rsi1h > 65:
            risks.append("overbought RSI")
        elif direction == "SHORT" and rsi1h < 35:
            risks.append("oversold RSI")
        best_vol = max(tech_details.get("volRatio1h", 1), tech_details.get("volRatio15m", 1))
        if best_vol < 0.5:
            risks.append("volume dying")
        elif best_vol < 0.7:
            risks.append("volume declining")
        if not fund_details["favorable"]:
            risks.append(f"funding against you ({fund_details['annualized']:+.1f}% ann)")
        if abs(tech_details.get("chg24h", 0)) > 5:
            risks.append("extended move, may revert")
        if sm_score < 10:
            risks.append("weak smart money signal")
        if ms_score < 20:
            risks.append("low volume/OI")
        # Trend counter warning
        trend = tech_details.get("trend4h", "neutral")
        if direction == "LONG" and trend in ("strong_down", "down"):
            risks.append("counter-trend (4h downtrend)")
        elif direction == "SHORT" and trend in ("strong_up", "up"):
            risks.append("counter-trend (4h uptrend)")
        # Divergence warning
        div = tech_details.get("divergence")
        if div == "bullish" and direction == "SHORT":
            risks.append("bullish vol divergence (15m)")
        elif div == "bearish" and direction == "LONG":
            risks.append("bearish vol divergence (15m)")
        
        results.append({
            "asset": name,
            "direction": direction,
            "leverage": lev,
            "finalScore": final,
            "pillarScores": {
                "smartMoney": sm_score,
                "marketStructure": ms_score,
                "technicals": tech_score,
                "funding": fund_score
            },
            "smartMoney": sm_details,
            "marketStructure": ms_details,
            "technicals": tech_details,
            "funding": fund_details,
            "markPrice": assets[name]["markPrice"],
            "risks": risks
        })
        
        print(f"  {name}: done (4h={len(candles_4h)} 1h={len(candles_1h)} 15m={len(candles_15m)} candles)", file=sys.stderr)
        
    except Exception as e:
        print(f"  {name}: failed ({e})", file=sys.stderr)
        continue

# Sort by final score
results.sort(key=lambda x: x["finalScore"], reverse=True)

# ═══════════════════════════════════════════
# OUTPUT
# ═══════════════════════════════════════════

output = {
    "scanTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "assetsScanned": len(meta_info),
    "passedStage1": len(assets),
    "passedStage2": len(top_assets),
    "deepDived": len(results),
    "pillarWeights": {
        "smartMoney": W_SMART_MONEY,
        "marketStructure": W_MARKET_STRUCTURE,
        "technicals": W_TECHNICALS,
        "funding": W_FUNDING
    },
    "opportunities": results[:15]  # top 15
}

print(json.dumps(output, indent=2))
print(f"\nDone. {len(results)} scored opportunities.", file=sys.stderr)
