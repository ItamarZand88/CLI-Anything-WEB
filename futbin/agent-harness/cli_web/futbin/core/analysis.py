"""Market analysis utilities — price trend computation, signals, value metrics."""

from __future__ import annotations

import statistics


def compute_price_analysis(prices: list[list], current_price: int) -> dict:
    """Compute analysis metrics for a price series.

    Args:
        prices: List of [timestamp_ms, price] pairs
        current_price: Current market price (from detail page, more accurate)

    Returns dict with: min, max, avg_30d, price_position_pct, vs_avg_30d_pct,
                       trend_7d, trend_30d, volatility_30d, signal
    """
    if not prices or len(prices) < 7:
        return {}

    all_vals = [p[1] for p in prices]
    price_min = min(all_vals)
    price_max = max(all_vals)

    # Price position in historic range
    price_range = price_max - price_min
    position_pct = ((current_price - price_min) / price_range * 100) if price_range > 0 else 50.0

    # 30-day average (last 30 data points)
    recent_30 = all_vals[-30:] if len(all_vals) >= 30 else all_vals
    avg_30d = statistics.mean(recent_30)

    # Vs 30d average
    vs_avg_pct = ((current_price - avg_30d) / avg_30d * 100) if avg_30d > 0 else 0

    # 7-day trend
    recent_7 = all_vals[-7:] if len(all_vals) >= 7 else all_vals
    trend_7d = ((recent_7[-1] - recent_7[0]) / recent_7[0] * 100) if recent_7[0] > 0 else 0

    # 30-day trend
    trend_30d = ((recent_30[-1] - recent_30[0]) / recent_30[0] * 100) if recent_30[0] > 0 else 0

    # Volatility (coefficient of variation of 30d prices)
    volatility = (
        (statistics.stdev(recent_30) / avg_30d * 100) if len(recent_30) > 1 and avg_30d > 0 else 0
    )

    # Signal
    signal = "HOLD"
    if vs_avg_pct < -10 and trend_7d >= -2:
        signal = "BUY"
    elif vs_avg_pct > 15 and trend_7d < 0:
        signal = "SELL"

    return {
        "current": current_price,
        "min": price_min,
        "max": price_max,
        "avg_30d": round(avg_30d),
        "price_position_pct": round(position_pct, 1),
        "vs_avg_30d_pct": round(vs_avg_pct, 1),
        "trend_7d": round(trend_7d, 1),
        "trend_30d": round(trend_30d, 1),
        "volatility_30d": round(volatility, 1),
        "signal": signal,
    }


def compute_platform_gap(ps_price: int | None, pc_price: int | None) -> dict:
    """Compute cross-platform price gap."""
    if not ps_price or not pc_price or ps_price <= 0 or pc_price <= 0:
        return {"gap_pct": 0, "gap_coins": 0, "cheaper_on": "unknown"}

    gap = abs(ps_price - pc_price)
    gap_pct = (gap / min(ps_price, pc_price)) * 100
    cheaper = "ps" if ps_price < pc_price else "pc"

    return {
        "gap_pct": round(gap_pct, 1),
        "gap_coins": gap,
        "cheaper_on": cheaper,
    }


def compute_value_score(stats: dict, price: int | None) -> float | None:
    """Compute value score: total_stats / (price / 1000). Higher = better value."""
    if not stats or not price or price <= 0:
        return None
    total = sum(v for v in stats.values() if isinstance(v, (int, float)))
    if total == 0:
        return None
    return round(total / (price / 1000), 1)


def compute_total_stats(stats: dict) -> int:
    """Sum all face stat values (pac, sho, pas, dri, def, phy)."""
    if not stats:
        return 0
    return sum(v for v in stats.values() if isinstance(v, (int, float)))


def compute_coins_per_stat(total_stats: int, price: int | None) -> float | None:
    """Compute coins per stat point. Lower = better value."""
    if not total_stats or not price or price <= 0:
        return None
    return round(price / total_stats, 1)
