#!/usr/bin/env python3
"""Shadow-data analyzer for Chainstack grid-bot testnet trials.

Reads a SQLite DB produced by tools/shadow_collector.py and emits a
Markdown research report. Stdlib only.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

REQUIRED_TABLES = [
    "mids", "account_snapshots", "positions", "open_orders",
    "fills", "grid_snapshots", "rebalance_events", "bot_log",
    "resource_usage", "meta",
]

BUY_TOKENS = {"B", "b", "buy", "BUY", "Buy"}
SELL_TOKENS = {"A", "a", "sell", "SELL", "Sell"}


def is_buy(side: str | None) -> bool:
    if side is None:
        return False
    return side in BUY_TOKENS


def is_sell(side: str | None) -> bool:
    if side is None:
        return False
    return side in SELL_TOKENS


def fmt_price(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x:.2f}"


def fmt_pct(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x:.3f}"


def fmt_size(x: float | None) -> str:
    if x is None:
        return "N/A"
    return f"{x:.6f}"


def fmt_ts(ts: float | None) -> str:
    if ts is None:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    except Exception:
        return "N/A"


def ensure_schema(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    existing = {r["name"] for r in rows}
    missing = [t for t in REQUIRED_TABLES if t not in existing]
    return missing


def table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    except sqlite3.Error:
        return 0


def table_ts_range(conn: sqlite3.Connection, table: str) -> tuple[float | None, float | None]:
    try:
        r = conn.execute(f"SELECT MIN(ts) AS lo, MAX(ts) AS hi FROM {table}").fetchone()
        return r["lo"], r["hi"]
    except sqlite3.Error:
        return None, None


def section_metadata(conn: sqlite3.Connection) -> list[str]:
    out = ["## 1. Trial metadata", ""]
    try:
        rows = conn.execute("SELECT key, value FROM meta").fetchall()
    except sqlite3.Error:
        rows = []
    if not rows:
        out.append("No data.")
    else:
        out.append("| Key | Value |")
        out.append("|---|---|")
        for r in rows:
            v = (r["value"] or "").replace("|", "\\|").replace("\n", " ")
            out.append(f"| {r['key']} | {v} |")
    out.append("")

    # Global time span across tables
    lo_all: float | None = None
    hi_all: float | None = None
    for t in REQUIRED_TABLES:
        if t == "meta":
            continue
        lo, hi = table_ts_range(conn, t)
        if lo is not None and (lo_all is None or lo < lo_all):
            lo_all = lo
        if hi is not None and (hi_all is None or hi > hi_all):
            hi_all = hi
    if lo_all is not None and hi_all is not None:
        dur_h = (hi_all - lo_all) / 3600.0
        out.append(f"- Span: {fmt_ts(lo_all)} -> {fmt_ts(hi_all)} ({dur_h:.3f}h)")
    else:
        out.append("- Span: No data.")
    out.append("")
    out.append("Row counts:")
    out.append("")
    out.append("| Table | Rows |")
    out.append("|---|---|")
    for t in REQUIRED_TABLES:
        out.append(f"| {t} | {table_count(conn, t)} |")
    out.append("")
    return out


def minute_bucket_mids(conn: sqlite3.Connection, coin: str) -> list[tuple[int, float]]:
    rows = conn.execute(
        "SELECT ts, mid FROM mids WHERE asset=? AND mid IS NOT NULL ORDER BY ts ASC",
        (coin,),
    ).fetchall()
    buckets: dict[int, tuple[float, float]] = {}  # minute -> (last_ts, mid)
    for r in rows:
        m = int(r["ts"] // 60)
        prev = buckets.get(m)
        if prev is None or r["ts"] > prev[0]:
            buckets[m] = (r["ts"], r["mid"])
    return sorted((m, v[1]) for m, v in buckets.items())


def section_market(conn: sqlite3.Connection, coin: str) -> tuple[list[str], dict]:
    out = [f"## 2. Market conditions ({coin})", ""]
    ctx: dict = {}
    rows = conn.execute(
        "SELECT ts, mid, bid, ask FROM mids WHERE asset=? AND mid IS NOT NULL ORDER BY ts ASC",
        (coin,),
    ).fetchall()
    if not rows:
        out.append("No data.")
        out.append("")
        return out, ctx

    mids = [r["mid"] for r in rows]
    first, last = mids[0], mids[-1]
    lo, hi = min(mids), max(mids)
    cum_ret = (last / first - 1.0) * 100.0 if first else 0.0
    ctx["first"] = first
    ctx["last"] = last
    ctx["cum_ret"] = cum_ret

    out.append(f"- First mid: {fmt_price(first)}")
    out.append(f"- Last mid:  {fmt_price(last)}")
    out.append(f"- Min mid:   {fmt_price(lo)}")
    out.append(f"- Max mid:   {fmt_price(hi)}")
    out.append(f"- Cumulative return: {fmt_pct(cum_ret)}%")
    out.append("")

    bucketed = minute_bucket_mids(conn, coin)
    log_returns: list[float] = []
    per_hour_returns: dict[int, list[float]] = defaultdict(list)
    for i in range(1, len(bucketed)):
        m_prev, p_prev = bucketed[i - 1]
        m_cur, p_cur = bucketed[i]
        if p_prev > 0 and p_cur > 0:
            lr = math.log(p_cur / p_prev)
            log_returns.append(lr)
            per_hour_returns[m_cur // 60].append(lr)

    if len(log_returns) >= 2:
        sigma_1min = statistics.stdev(log_returns)
        sigma_1min_pct = sigma_1min * 100.0
        sigma_ann = sigma_1min * math.sqrt(525600) * 100.0
        out.append(f"- 1-min realized sigma: {fmt_pct(sigma_1min_pct)}%")
        out.append(f"- Annualized sigma:    {fmt_pct(sigma_ann)}%")
    else:
        out.append("- Realized volatility: insufficient 1-min samples.")

    hour_sigmas: list[float] = []
    for h, series in per_hour_returns.items():
        if len(series) >= 2:
            hour_sigmas.append(statistics.stdev(series) * 100.0)
    if hour_sigmas:
        out.append(f"- Rolling 1h sigma (mean): {fmt_pct(statistics.fmean(hour_sigmas))}%")
        out.append(f"- Rolling 1h sigma (max):  {fmt_pct(max(hour_sigmas))}%")
    else:
        out.append("- Rolling 1h sigma: insufficient data.")

    spreads_bps = []
    for r in rows:
        b, a, m = r["bid"], r["ask"], r["mid"]
        if b is not None and a is not None and m and m > 0:
            spreads_bps.append(10000.0 * (a - b) / m)
    if spreads_bps:
        out.append(f"- Avg bid-ask spread: {fmt_pct(statistics.fmean(spreads_bps))} bps ({len(spreads_bps)} samples)")
    else:
        out.append("- Avg bid-ask spread: no bid/ask captured.")

    # 1h excursions in percent
    hour_buckets: dict[int, list[float]] = defaultdict(list)
    for m, p in bucketed:
        hour_buckets[m // 60].append(p)
    excursions = []
    for h, prices in hour_buckets.items():
        if len(prices) >= 2:
            lo_h, hi_h = min(prices), max(prices)
            mid_h = (lo_h + hi_h) / 2.0
            if mid_h > 0:
                excursions.append(100.0 * (hi_h - lo_h) / mid_h)
    ctx["excursions_1h"] = excursions
    out.append("")
    return out, ctx


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    f = int(math.floor(k))
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def section_grid(conn: sqlite3.Connection, coin: str, cfg_range_pct: float | None,
                 excursions_1h: list[float]) -> tuple[list[str], dict]:
    out = ["## 3. Grid configuration fit", ""]
    ctx: dict = {}
    rows = conn.execute(
        "SELECT ts, center_px, n_buy, n_sell, min_px, max_px, spread_pct "
        "FROM grid_snapshots WHERE coin=? ORDER BY ts ASC",
        (coin,),
    ).fetchall()
    if not rows:
        out.append("No grid snapshots.")
    else:
        def stats_of(field: str) -> tuple[float, float, float]:
            vals = [r[field] for r in rows if r[field] is not None]
            if not vals:
                return (float("nan"),) * 3
            return (statistics.fmean(vals), min(vals), max(vals))

        out.append("| Metric | Mean | Min | Max |")
        out.append("|---|---|---|---|")
        for f in ("center_px", "spread_pct", "n_buy", "n_sell"):
            m, lo, hi = stats_of(f)
            if math.isnan(m):
                out.append(f"| {f} | N/A | N/A | N/A |")
            else:
                out.append(f"| {f} | {m:.4f} | {lo:.4f} | {hi:.4f} |")
    out.append("")

    if cfg_range_pct is None:
        out.append("Range comparison: config not supplied, skipped.")
    elif not excursions_1h:
        out.append("Range comparison: no 1h price samples available.")
    else:
        full_width = 2.0 * cfg_range_pct
        p50 = percentile(excursions_1h, 0.50)
        p90 = percentile(excursions_1h, 0.90)
        p99 = percentile(excursions_1h, 0.99)
        ctx["excursion_p90"] = p90
        out.append(f"Configured full grid width: {full_width:.3f}%")
        out.append("")
        out.append("| Percentile | 1h excursion % | Ratio to grid width |")
        out.append("|---|---|---|")
        for label, v in (("p50", p50), ("p90", p90), ("p99", p99)):
            if v is None:
                out.append(f"| {label} | N/A | N/A |")
            else:
                out.append(f"| {label} | {v:.3f} | {(v / full_width):.3f} |")
    out.append("")

    reb = conn.execute(
        "SELECT ts FROM rebalance_events WHERE coin=? ORDER BY ts ASC", (coin,)
    ).fetchall()
    ctx["rebalance_count"] = len(reb)
    if not reb:
        out.append("Rebalance events: 0.")
    else:
        ts_list = [r["ts"] for r in reb]
        gaps = [ts_list[i] - ts_list[i - 1] for i in range(1, len(ts_list))]
        mean_gap = statistics.fmean(gaps) if gaps else float("nan")
        out.append(f"Rebalance events: {len(ts_list)}")
        if gaps:
            out.append(f"- Mean gap between rebalances: {mean_gap:.1f}s ({mean_gap/3600:.3f}h)")
        out.append(f"- First: {fmt_ts(ts_list[0])}  Last: {fmt_ts(ts_list[-1])}")
        # frequency per hour — use full trial span, not gap between events
        lo_all: float | None = None
        hi_all: float | None = None
        for t in REQUIRED_TABLES:
            if t == "meta":
                continue
            lo, hi = table_ts_range(conn, t)
            if lo is not None and (lo_all is None or lo < lo_all):
                lo_all = lo
            if hi is not None and (hi_all is None or hi > hi_all):
                hi_all = hi
        trial_hours = ((hi_all - lo_all) / 3600.0) if (lo_all is not None and hi_all is not None) else 0.0
        if trial_hours > 0:
            ctx["rebalance_per_hour"] = len(ts_list) / trial_hours
    out.append("")
    return out, ctx


def section_fills(conn: sqlite3.Connection, coin: str,
                  cfg_levels: int | None) -> tuple[list[str], dict]:
    out = ["## 4. Fills and realized P&L", ""]
    ctx: dict = {}
    rows = conn.execute(
        "SELECT ts, oid, side, coin, px, sz, fee, closed_pnl "
        "FROM fills WHERE coin=? ORDER BY ts ASC",
        (coin,),
    ).fetchall()
    if not rows:
        out.append("No fills recorded.")
        out.append("")
        ctx["fills_count"] = 0
        return out, ctx

    buys = [r for r in rows if is_buy(r["side"])]
    sells = [r for r in rows if is_sell(r["side"])]
    volume = sum(abs((r["px"] or 0) * (r["sz"] or 0)) for r in rows)
    fees = sum((r["fee"] or 0.0) for r in rows)
    cpnl = sum((r["closed_pnl"] or 0.0) for r in rows)
    net = cpnl - fees

    ctx["fills_count"] = len(rows)
    ctx["fees"] = fees
    ctx["closed_pnl"] = cpnl
    ctx["net_pnl"] = net

    out.append(f"- Total fills: {len(rows)} (buys={len(buys)}, sells={len(sells)})")
    out.append(f"- Total notional volume: ${volume:.2f}")
    out.append(f"- Total fees: ${fees:.6f}")
    out.append(f"- Sum closed_pnl: ${cpnl:.6f}")
    out.append(f"- Net realized PnL (closed_pnl - fees): ${net:.6f}")

    def vwap(rs):
        num = sum((r["px"] or 0) * (r["sz"] or 0) for r in rs)
        den = sum(r["sz"] or 0 for r in rs)
        return (num / den) if den else None

    bvw = vwap(buys)
    svw = vwap(sells)
    out.append(f"- Buy VWAP:  {fmt_price(bvw)}")
    out.append(f"- Sell VWAP: {fmt_price(svw)}")
    if bvw and svw and bvw > 0:
        implied = (svw - bvw) / bvw * 100.0
        out.append(f"- Implied round-trip spread: {fmt_pct(implied)}%")
    out.append("")

    # Per-hour histogram
    per_hour: Counter = Counter()
    for r in rows:
        per_hour[int(r["ts"] // 3600)] += 1
    top = per_hour.most_common(10)
    out.append("Top 10 hours by fill count:")
    out.append("")
    out.append("| Hour (UTC) | Fills |")
    out.append("|---|---|")
    for h, n in top:
        out.append(f"| {fmt_ts(h * 3600)} | {n} |")
    out.append("")
    # mean fills per hour
    if per_hour:
        ctx["mean_fills_per_hour"] = statistics.fmean(per_hour.values())

    # Level histogram
    lvl_rows = conn.execute(
        "SELECT DISTINCT px FROM open_orders WHERE coin=? AND px IS NOT NULL ORDER BY px ASC",
        (coin,),
    ).fetchall()
    levels = sorted({r["px"] for r in lvl_rows if r["px"] is not None})
    if not levels:
        out.append("Per-level histogram: no open_orders levels observed.")
    else:
        counts: Counter = Counter()
        for r in rows:
            if r["px"] is None:
                continue
            # nearest level
            nearest = min(levels, key=lambda L: abs(L - r["px"]))
            counts[nearest] += 1
        out.append(f"Per-level fill histogram ({len(levels)} distinct levels observed):")
        out.append("")
        out.append("| Level price | Fills |")
        out.append("|---|---|")
        for L in levels:
            out.append(f"| {fmt_price(L)} | {counts.get(L, 0)} |")
        if cfg_levels is not None:
            out.append("")
            out.append(f"Config `levels` = {cfg_levels}; observed distinct levels = {len(levels)}.")

        # central-50% concentration metric
        if levels and sum(counts.values()) > 0:
            n = len(levels)
            lo_idx = n // 4
            hi_idx = n - (n // 4)
            central_levels = levels[lo_idx:hi_idx] if hi_idx > lo_idx else levels
            central_sum = sum(counts.get(L, 0) for L in central_levels)
            total = sum(counts.values())
            ctx["central_ratio"] = central_sum / total if total else 0.0
    out.append("")
    return out, ctx


def section_equity(conn: sqlite3.Connection) -> list[str]:
    out = ["## 5. Equity curve", ""]
    rows = conn.execute(
        "SELECT ts, equity, margin_used FROM account_snapshots "
        "WHERE equity IS NOT NULL ORDER BY ts ASC"
    ).fetchall()
    if not rows:
        out.append("No data.")
        out.append("")
        return out
    eqs = [r["equity"] for r in rows]
    first_eq, last_eq = eqs[0], eqs[-1]
    max_eq, min_eq = max(eqs), min(eqs)
    peak = -math.inf
    max_dd = 0.0
    for e in eqs:
        if e > peak:
            peak = e
        if peak > 0:
            dd = (peak - e) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    out.append(f"- First equity: ${first_eq:.4f}")
    out.append(f"- Last equity:  ${last_eq:.4f}")
    out.append(f"- Max equity:   ${max_eq:.4f}")
    out.append(f"- Min equity:   ${min_eq:.4f}")
    out.append(f"- Max drawdown: {fmt_pct(max_dd)}%")
    out.append("")

    n = len(rows)
    k = min(10, n)
    indices = [int(round(i * (n - 1) / (k - 1))) for i in range(k)] if k > 1 else [0]
    out.append("Sampled equity trajectory:")
    out.append("")
    out.append("| ts | equity | margin_used |")
    out.append("|---|---|---|")
    for idx in indices:
        r = rows[idx]
        mu = r["margin_used"]
        mu_s = f"{mu:.4f}" if mu is not None else "N/A"
        out.append(f"| {fmt_ts(r['ts'])} | {r['equity']:.4f} | {mu_s} |")
    out.append("")
    return out


def section_bot_vs_reality(conn: sqlite3.Connection, fills_count: int,
                           net_pnl: float | None) -> list[str]:
    out = ["## 6. Bot reported vs. reality", ""]
    logs = conn.execute("SELECT ts, level, message FROM bot_log ORDER BY ts ASC").fetchall()
    if not logs:
        out.append("No bot_log entries.")
        out.append("")
        return out

    total_trades_re = re.compile(r"Total trades:\s*(\d+)")
    placed_re = re.compile(r"Placed\s+(BUY|SELL)\s+order", re.IGNORECASE)
    profit_re = re.compile(r"(total_profit|profit)[^\d\-]*(-?\d+\.?\d*)", re.IGNORECASE)

    last_total_trades: int | None = None
    placed_count = 0
    bot_profits: list[tuple[float, str, float]] = []
    for r in logs:
        msg = r["message"] or ""
        m = total_trades_re.search(msg)
        if m:
            try:
                last_total_trades = int(m.group(1))
            except ValueError:
                pass
        if placed_re.search(msg):
            placed_count += 1
        pm = profit_re.search(msg)
        if pm:
            try:
                bot_profits.append((r["ts"], pm.group(1), float(pm.group(2))))
            except ValueError:
                pass

    out.append(f"- Bot-reported `Total trades` (last seen): {last_total_trades if last_total_trades is not None else 'not found'}")
    out.append(f"- 'Placed BUY/SELL order' log lines: {placed_count}")
    out.append(f"- Actual fills recorded: {fills_count}")
    if last_total_trades is not None:
        gap = last_total_trades - fills_count
        out.append(f"- Gap (bot_reported_trades - fills): {gap}")
        out.append("  - Interpretation: bot's `executed_trades` counts orders SUBMITTED, not exchange fills."
                   " Gap = pending orders + orders that never filled (see engine.py:394-399).")
    out.append("")

    if bot_profits:
        last_ts, last_key, last_val = bot_profits[-1]
        out.append(f"- Bot-reported profit (last `{last_key}`): {last_val:.6f} at {fmt_ts(last_ts)}")
        if net_pnl is not None:
            out.append(f"- Fill-derived Net Realized PnL: {net_pnl:.6f}")
            out.append("  - Bot's profit formula is a placeholder (1% of sell notional — see basic_grid.py:253-257)."
                       " Treat bot-reported profit as fictional.")
    else:
        out.append("- No 'profit' log lines found.")
    out.append("")
    return out


def section_inventory(conn: sqlite3.Connection, coin: str) -> tuple[list[str], dict]:
    out = ["## 7. Inventory drift", ""]
    ctx: dict = {}
    prows = conn.execute(
        "SELECT ts, size FROM positions WHERE asset=? AND size IS NOT NULL ORDER BY ts ASC",
        (coin,),
    ).fetchall()
    if not prows:
        out.append("No position data.")
        out.append("")
        return out, ctx
    sizes = [r["size"] for r in prows]
    out.append(f"- Position size — min: {fmt_size(min(sizes))}, max: {fmt_size(max(sizes))}, "
               f"mean: {fmt_size(statistics.fmean(sizes))}, final: {fmt_size(sizes[-1])}")

    bucketed_mids = dict(minute_bucket_mids(conn, coin))
    if not bucketed_mids:
        out.append("- No mid data to correlate.")
        out.append("")
        return out, ctx

    pos_by_min: dict[int, float] = {}
    for r in prows:
        m = int(r["ts"] // 60)
        pos_by_min[m] = r["size"]

    xs: list[float] = []
    ys: list[float] = []
    for m, sz in pos_by_min.items():
        # nearest minute bucket in mids
        if m in bucketed_mids:
            xs.append(sz)
            ys.append(bucketed_mids[m])
        else:
            # find nearest within 5 minutes — symmetric; on tie prefer -dm
            best = None
            for dm in range(1, 6):
                has_neg = (m - dm) in bucketed_mids
                has_pos = (m + dm) in bucketed_mids
                if has_neg:
                    best = bucketed_mids[m - dm]; break
                if has_pos:
                    best = bucketed_mids[m + dm]; break
            if best is not None:
                xs.append(sz)
                ys.append(best)

    if len(xs) >= 2 and statistics.pstdev(xs) > 0 and statistics.pstdev(ys) > 0:
        mx = statistics.fmean(xs); my = statistics.fmean(ys)
        num = sum((xs[i] - mx) * (ys[i] - my) for i in range(len(xs)))
        dxs = math.sqrt(sum((v - mx) ** 2 for v in xs))
        dys = math.sqrt(sum((v - my) ** 2 for v in ys))
        if dxs > 0 and dys > 0:
            corr = num / (dxs * dys)
            ctx["pos_price_corr"] = corr
            out.append(f"- Pearson correlation (size vs mid): {corr:.4f} (n={len(xs)})")
            out.append("  - Positive correlation = bot accumulates inventory as price rises (trend-exposed, bad for a grid).")
    else:
        out.append("- Correlation: insufficient variance or samples.")
    out.append("")
    return out, ctx


def section_resource(conn: sqlite3.Connection) -> list[str]:
    out = ["## 8. Resource usage", ""]
    rows = conn.execute(
        "SELECT cpu_pct, mem_mb FROM resource_usage WHERE cpu_pct IS NOT NULL OR mem_mb IS NOT NULL"
    ).fetchall()
    if not rows:
        out.append("No data.")
        out.append("")
        return out
    cpus = [r["cpu_pct"] for r in rows if r["cpu_pct"] is not None]
    mems = [r["mem_mb"] for r in rows if r["mem_mb"] is not None]
    if cpus:
        out.append(f"- CPU %: mean {statistics.fmean(cpus):.3f}, max {max(cpus):.3f}")
    if mems:
        out.append(f"- Memory MB: mean {statistics.fmean(mems):.3f}, max {max(mems):.3f} (docker limit: 512MB)")
    out.append("")
    return out


def section_errors(conn: sqlite3.Connection) -> list[str]:
    out = ["## 9. Error summary", ""]
    rows = conn.execute("SELECT level, message FROM bot_log").fetchall()
    if not rows:
        out.append("No bot_log entries.")
        out.append("")
        return out
    n_warn = sum(1 for r in rows if (r["level"] or "").upper() == "WARNING")
    n_err = sum(1 for r in rows if (r["level"] or "").upper() == "ERROR")
    out.append(f"- WARNING lines: {n_warn}")
    out.append(f"- ERROR lines:   {n_err}")

    err_msgs = Counter((r["message"] or "").strip()
                       for r in rows if (r["level"] or "").upper() == "ERROR")
    if err_msgs:
        out.append("")
        out.append("Top distinct error messages:")
        out.append("")
        out.append("| Count | Message |")
        out.append("|---|---|")
        for msg, n in err_msgs.most_common(5):
            snip = msg[:120].replace("|", "\\|")
            out.append(f"| {n} | {snip} |")

    kws = ("disconnect", "reconnect", "traceback")
    out.append("")
    out.append("Keyword counts (case-insensitive, any level):")
    for kw in kws:
        c = sum(1 for r in rows if kw in (r["message"] or "").lower())
        out.append(f"- {kw}: {c}")
    out.append("")
    return out


def section_heuristics(cfg_range_pct: float | None, market_ctx: dict,
                       grid_ctx: dict, fills_ctx: dict,
                       inv_ctx: dict) -> list[str]:
    out = ["## 10. Suggested parameter adjustments", ""]
    any_fired = False

    excursions = market_ctx.get("excursions_1h", [])
    p90 = percentile(excursions, 0.90) if excursions else None
    if cfg_range_pct is not None and p90 is not None and p90 > cfg_range_pct:
        out.append(f"- Consider widening `range_pct`: realized p90 1h excursion = {p90:.3f}% vs current +/-{cfg_range_pct}%.")
        any_fired = True

    mean_fph = fills_ctx.get("mean_fills_per_hour")
    # No direct spread_pct value; rely on mean fills alone
    if mean_fph is not None and mean_fph < 0.5:
        out.append(f"- Grid may be too tight or market too quiet: mean fills/hour = {mean_fph:.3f} (<0.5).")
        any_fired = True

    corr = inv_ctx.get("pos_price_corr")
    if corr is not None and corr > 0.5:
        out.append(f"- Strong trend exposure: size~mid correlation = {corr:.3f} (>0.5); add a trend filter or widen range.")
        any_fired = True

    rph = grid_ctx.get("rebalance_per_hour")
    if rph is not None and rph > 1.0:
        out.append(f"- Too much rebalancing thrash: {rph:.3f} rebalances/hour (>1/h).")
        any_fired = True

    fees = fills_ctx.get("fees", 0.0)
    cpnl = fills_ctx.get("closed_pnl", 0.0)
    if cpnl and abs(cpnl) > 0 and fees > 0.5 * abs(cpnl):
        out.append(f"- Fee drag >50% of gross: fees={fees:.6f}, |closed_pnl|={abs(cpnl):.6f}.")
        any_fired = True

    central = fills_ctx.get("central_ratio")
    if central is not None and central >= 0.8 and fills_ctx.get("fills_count", 0) > 0:
        out.append("- 80%+ of fills in central 50% of levels; edge levels idle — capital inefficient.")
        any_fired = True

    if fills_ctx.get("fills_count", 0) == 0:
        out.append("- No fills observed — market never moved past nearest level, or fill detection differs. "
                   "Check price move vs level spacing.")
        any_fired = True

    if not any_fired:
        out.append("No heuristic triggers fired.")
    out.append("")
    return out


def section_raw(conn: sqlite3.Connection) -> list[str]:
    out = ["## 11. Raw data summaries", ""]
    out.append("| Table | Rows | Min ts | Max ts |")
    out.append("|---|---|---|---|")
    for t in REQUIRED_TABLES:
        if t == "meta":
            n = table_count(conn, t)
            out.append(f"| {t} | {n} | N/A | N/A |")
            continue
        n = table_count(conn, t)
        lo, hi = table_ts_range(conn, t)
        out.append(f"| {t} | {n} | {fmt_ts(lo)} | {fmt_ts(hi)} |")
    out.append("")
    return out


def build_report(db_path: str, coin: str, cfg_range_pct: float | None,
                 cfg_levels: int | None) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        missing = ensure_schema(conn)
        if missing:
            raise SystemExit(f"ERROR: DB at {db_path} is missing required tables: {missing}")

        lines: list[str] = []
        lines.append(f"# Shadow Analysis Report")
        lines.append("")
        lines.append(f"- DB: `{db_path}`")
        lines.append(f"- Coin: `{coin}`")
        lines.append(f"- Config range_pct: {cfg_range_pct if cfg_range_pct is not None else 'not supplied'}")
        lines.append(f"- Config levels: {cfg_levels if cfg_levels is not None else 'not supplied'}")
        lines.append(f"- Generated: {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')}")
        lines.append("")

        lines += section_metadata(conn)
        market_lines, market_ctx = section_market(conn, coin)
        lines += market_lines
        grid_lines, grid_ctx = section_grid(conn, coin, cfg_range_pct, market_ctx.get("excursions_1h", []))
        lines += grid_lines
        fills_lines, fills_ctx = section_fills(conn, coin, cfg_levels)
        lines += fills_lines
        lines += section_equity(conn)
        lines += section_bot_vs_reality(conn, fills_ctx.get("fills_count", 0), fills_ctx.get("net_pnl"))
        inv_lines, inv_ctx = section_inventory(conn, coin)
        lines += inv_lines
        lines += section_resource(conn)
        lines += section_errors(conn)
        lines += section_heuristics(cfg_range_pct, market_ctx, grid_ctx, fills_ctx, inv_ctx)
        lines += section_raw(conn)

        return "\n".join(lines) + "\n"
    finally:
        conn.close()


def default_out_path(db_path: str) -> str:
    base, _ = os.path.splitext(db_path)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{base}-report-{stamp}.md"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Analyze shadow-collector SQLite DB and emit a Markdown report.")
    p.add_argument("db_path", help="Path to the SQLite DB produced by shadow_collector.py")
    p.add_argument("--out", default=None, help="Output Markdown path (default: <db>-report-<UTCstamp>.md)")
    p.add_argument("--coin", default="BTC", help="Asset to analyze (default: BTC)")
    p.add_argument("--config-range-pct", type=float, default=None,
                   help="Configured range_pct (for comparison only)")
    p.add_argument("--config-levels", type=int, default=None,
                   help="Configured levels count (for comparison only)")
    args = p.parse_args(argv)

    if not os.path.exists(args.db_path):
        print(f"ERROR: DB not found: {args.db_path}", file=sys.stderr)
        return 2

    try:
        report = build_report(args.db_path, args.coin, args.config_range_pct, args.config_levels)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 3

    out_path = args.out or default_out_path(args.db_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Wrote report to: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
