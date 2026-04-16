#!/usr/bin/env python3
"""Shadow collector for Chainstack Grid Bot testnet trial.

Runs on the host alongside the dockerized bot. Read-only HL polling plus docker
log/stat tailing. Writes a SQLite research DB for offline analysis.

Concurrency model: one dedicated writer thread owns the sqlite connection and
drains a queue of (sql, params) work items. All worker threads enqueue writes.
"""

import argparse
import json
import logging
import os
import queue
import re
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from eth_account import Account
from hyperliquid.info import Info
from hyperliquid.utils.constants import TESTNET_API_URL


COLLECTOR_VERSION = "1.0"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONTAINER = "sandbox-bot-testnet-chainstack-1"

log = logging.getLogger("shadow_collector")

stopping = threading.Event()
write_q: "queue.Queue[Optional[tuple[str, tuple]]]" = queue.Queue(maxsize=10000)
_last_full_warn_ts: float = 0.0
_subprocs: list[subprocess.Popen] = []
_last_ws_cb_ts: float = 0.0  # updated from SDK WS thread; read by watchdog

SCHEMA = """
CREATE TABLE IF NOT EXISTS mids (
  ts REAL NOT NULL, asset TEXT NOT NULL, mid REAL NOT NULL, bid REAL, ask REAL
);
CREATE INDEX IF NOT EXISTS idx_mids_ts ON mids(ts);
CREATE INDEX IF NOT EXISTS idx_mids_asset_ts ON mids(asset, ts);

CREATE TABLE IF NOT EXISTS account_snapshots (
  ts REAL NOT NULL, equity REAL, withdrawable REAL, margin_used REAL, raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_account_ts ON account_snapshots(ts);

CREATE TABLE IF NOT EXISTS positions (
  ts REAL NOT NULL, asset TEXT NOT NULL, size REAL NOT NULL, entry_px REAL,
  unrealized_pnl REAL, leverage_type TEXT, leverage_value REAL
);
CREATE INDEX IF NOT EXISTS idx_positions_ts ON positions(ts);

CREATE TABLE IF NOT EXISTS open_orders (
  ts REAL NOT NULL, oid INTEGER NOT NULL, side TEXT NOT NULL, coin TEXT NOT NULL,
  px REAL NOT NULL, sz REAL NOT NULL, reduce_only INTEGER, order_type TEXT, raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_open_orders_ts ON open_orders(ts);
CREATE INDEX IF NOT EXISTS idx_open_orders_oid ON open_orders(oid);

CREATE TABLE IF NOT EXISTS fills (
  tid INTEGER PRIMARY KEY, ts REAL NOT NULL, oid INTEGER, side TEXT NOT NULL,
  coin TEXT NOT NULL, px REAL NOT NULL, sz REAL NOT NULL, fee REAL, closed_pnl REAL,
  start_position REAL, dir TEXT, hash TEXT, raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_fills_ts ON fills(ts);

CREATE TABLE IF NOT EXISTS grid_snapshots (
  ts REAL NOT NULL, coin TEXT NOT NULL, center_px REAL, n_buy INTEGER NOT NULL,
  n_sell INTEGER NOT NULL, min_px REAL, max_px REAL, spread_pct REAL
);
CREATE INDEX IF NOT EXISTS idx_grid_ts ON grid_snapshots(ts);

CREATE TABLE IF NOT EXISTS rebalance_events (
  ts REAL NOT NULL, coin TEXT NOT NULL, old_center REAL, new_center REAL,
  n_cancelled INTEGER, n_placed INTEGER
);
CREATE INDEX IF NOT EXISTS idx_rebalance_ts ON rebalance_events(ts);

CREATE TABLE IF NOT EXISTS bot_log (
  ts REAL NOT NULL, level TEXT, message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bot_log_ts ON bot_log(ts);

CREATE TABLE IF NOT EXISTS resource_usage (
  ts REAL NOT NULL, cpu_pct REAL, mem_mb REAL
);
CREATE INDEX IF NOT EXISTS idx_resource_ts ON resource_usage(ts);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY, value TEXT NOT NULL
);
"""

TABLES = [
    "mids", "account_snapshots", "positions", "open_orders", "fills",
    "grid_snapshots", "rebalance_events", "bot_log", "resource_usage", "meta",
]


def _to_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def normalize_side(s: Any) -> str:
    """Map HL side codes to 'B' or 'A'."""
    if not s:
        return ""
    v = str(s).strip().lower()
    if v in ("b", "buy", "bid", "long"):
        return "B"
    if v in ("a", "s", "sell", "ask", "short"):
        return "A"
    return str(s)


def derive_address_from_env() -> str:
    key = os.getenv("HYPERLIQUID_TESTNET_PRIVATE_KEY") or os.getenv("HL_PRIVATE_KEY")
    if not key:
        log.error("No private key in env; set HYPERLIQUID_TESTNET_PRIVATE_KEY or HL_PRIVATE_KEY, or pass --address")
        sys.exit(2)
    if not key.startswith("0x"):
        key = "0x" + key
    return Account.from_key(key).address


def enqueue(sql: str, params: tuple) -> None:
    global _last_full_warn_ts
    if stopping.is_set():
        return
    try:
        write_q.put((sql, params), block=True, timeout=5.0)
    except queue.Full:
        now = time.time()
        if now - _last_full_warn_ts > 10.0:
            _last_full_warn_ts = now
            log.warning("write queue full (maxsize=10000); dropping row")


def writer_thread(db_path: Path) -> None:
    """Single writer: owns the sqlite connection."""
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(SCHEMA)
        conn.commit()
    except Exception as e:
        log.error("writer: failed to open DB %s: %s", db_path, e)
        os._exit(3)

    batch_commit_at = time.time() + 1.0
    pending = 0
    while True:
        try:
            item = write_q.get(timeout=0.5)
        except queue.Empty:
            if pending:
                conn.commit()
                pending = 0
            continue
        if item is None:
            break
        sql, params = item
        try:
            conn.execute(sql, params)
            pending += 1
        except Exception as e:
            log.warning("writer: sql failed: %s | %s", e, sql[:80])
        if pending >= 50 or time.time() >= batch_commit_at:
            try:
                conn.commit()
            except Exception as e:
                log.warning("writer: commit failed: %s", e)
            pending = 0
            batch_commit_at = time.time() + 1.0

    try:
        conn.commit()
    except Exception:
        pass
    try:
        conn.close()
    except Exception:
        pass


def insert_meta(key: str, value: str) -> None:
    enqueue(
        "INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)",
        (key, value),
    )


# ---------------- Workers ----------------

def _handle_mids_payload(payload: Any, watched: set[str]) -> None:
    """Accept SDK allMids callback data or info.all_mids() dict."""
    now = time.time()
    if isinstance(payload, dict) and "data" in payload:
        data = payload.get("data") or {}
        mids = data.get("mids") if isinstance(data, dict) else None
        if mids is None and isinstance(data, dict):
            mids = data
    else:
        mids = payload
    if not isinstance(mids, dict):
        return
    for asset in watched:
        v = mids.get(asset)
        f = _to_float(v)
        if f is None:
            continue
        enqueue(
            "INSERT INTO mids(ts, asset, mid, bid, ask) VALUES(?, ?, ?, NULL, NULL)",
            (now, asset, f),
        )


def mids_ws_thread(assets: list[str]) -> None:
    """SDK WS for allMids, polling fallback on failure."""
    watched = set(assets)
    info_ws: Optional[Info] = None
    try:
        info_ws = Info(TESTNET_API_URL, skip_ws=False, spot_meta={"universe": [], "tokens": []})

        def on_mids(msg: Any) -> None:
            global _last_ws_cb_ts
            _last_ws_cb_ts = time.time()
            try:
                _handle_mids_payload(msg, watched)
            except Exception as e:
                log.debug("mids callback error: %s", e)

        info_ws.subscribe({"type": "allMids"}, on_mids)
        log.info("mids: WS subscribed")
        try:
            while not stopping.wait(1.0):
                pass
            return
        finally:
            try:
                info_ws.disconnect_websocket()
            except AttributeError:
                try:
                    info_ws.ws_manager.stop()
                except AttributeError:
                    pass
                except Exception as e:
                    log.debug("mids: ws_manager stop error: %s", e)
            except Exception as e:
                log.debug("mids: disconnect error: %s", e)
    except Exception as e:
        log.warning("mids: WS unavailable, falling back to 2s polling: %s", e)

    try:
        info_poll = Info(TESTNET_API_URL, skip_ws=True, spot_meta={"universe": [], "tokens": []})
    except Exception as e:
        log.error("mids: cannot create polling Info: %s", e)
        return
    while not stopping.is_set():
        try:
            mids = info_poll.all_mids()
            _handle_mids_payload(mids, watched)
        except Exception as e:
            log.warning("mids poll failed: %s", e)
        if stopping.wait(2.0):
            break


def account_thread(info: Info, address: str) -> None:
    while not stopping.is_set():
        try:
            state = info.user_state(address)
            now = time.time()
            margin = (state or {}).get("marginSummary", {}) or {}
            equity = _to_float(margin.get("accountValue"))
            withdrawable = _to_float((state or {}).get("withdrawable"))
            if withdrawable is None:
                withdrawable = _to_float(margin.get("withdrawable"))
            margin_used = _to_float(margin.get("totalMarginUsed"))
            enqueue(
                "INSERT INTO account_snapshots(ts, equity, withdrawable, margin_used, raw_json) VALUES(?,?,?,?,?)",
                (now, equity, withdrawable, margin_used, json.dumps(state)),
            )
            for pos in (state or {}).get("assetPositions", []) or []:
                p = pos.get("position", {}) or {}
                lev = p.get("leverage") or {}
                enqueue(
                    "INSERT INTO positions(ts, asset, size, entry_px, unrealized_pnl, leverage_type, leverage_value) VALUES(?,?,?,?,?,?,?)",
                    (
                        now,
                        str(p.get("coin", "")),
                        _to_float(p.get("szi"), 0.0) or 0.0,
                        _to_float(p.get("entryPx")),
                        _to_float(p.get("unrealizedPnl")),
                        str(lev.get("type")) if lev.get("type") is not None else None,
                        _to_float(lev.get("value")),
                    ),
                )
        except Exception as e:
            log.warning("account: %s", e)
        if stopping.wait(30.0):
            break


# Rebalance detection state (module-level; only orders_thread touches it).
_prev_oids: set[int] = set()
_prev_centers: dict[str, float] = {}


def orders_thread(info: Info, address: str) -> None:
    global _prev_oids, _prev_centers
    while not stopping.is_set():
        try:
            orders = info.open_orders(address) or []
            now = time.time()
            cur_oids: set[int] = set()
            by_coin: dict[str, list[dict]] = {}
            for o in orders:
                oid = o.get("oid")
                if oid is None:
                    continue
                try:
                    oid_i = int(oid)
                except (TypeError, ValueError):
                    continue
                cur_oids.add(oid_i)
                coin = str(o.get("coin", ""))
                side = normalize_side(o.get("side"))
                px = _to_float(o.get("limitPx"), 0.0) or 0.0
                sz = _to_float(o.get("sz"), 0.0) or 0.0
                reduce_only = 1 if o.get("reduceOnly") else 0
                order_type = o.get("orderType")
                enqueue(
                    "INSERT INTO open_orders(ts, oid, side, coin, px, sz, reduce_only, order_type, raw_json) VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        now, oid_i, side, coin, px, sz, reduce_only,
                        str(order_type) if order_type is not None else None,
                        json.dumps(o),
                    ),
                )
                by_coin.setdefault(coin, []).append({"side": side, "px": px, "sz": sz})

            new_centers: dict[str, float] = {}
            for coin, coin_orders in by_coin.items():
                pxs = [r["px"] for r in coin_orders if r["px"] > 0]
                if not pxs:
                    continue
                n_buy = sum(1 for r in coin_orders if r["side"] == "B")
                n_sell = sum(1 for r in coin_orders if r["side"] == "A")
                min_px = min(pxs)
                max_px = max(pxs)
                center = (min_px + max_px) / 2.0
                spread_pct = 100.0 * (max_px - min_px) / center if center else 0.0
                enqueue(
                    "INSERT INTO grid_snapshots(ts, coin, center_px, n_buy, n_sell, min_px, max_px, spread_pct) VALUES(?,?,?,?,?,?,?,?)",
                    (now, coin, center, n_buy, n_sell, min_px, max_px, spread_pct),
                )
                new_centers[coin] = center

            cancelled = _prev_oids - cur_oids
            placed = cur_oids - _prev_oids
            if len(cancelled) >= 3 and len(placed) >= 3:
                for coin, new_center in new_centers.items():
                    old_center = _prev_centers.get(coin)
                    if old_center is not None and abs(old_center - new_center) > 1e-9:
                        enqueue(
                            "INSERT INTO rebalance_events(ts, coin, old_center, new_center, n_cancelled, n_placed) VALUES(?,?,?,?,?,?)",
                            (now, coin, old_center, new_center, len(cancelled), len(placed)),
                        )
            _prev_oids = cur_oids
            if new_centers:
                _prev_centers.update(new_centers)
        except Exception as e:
            log.warning("orders: %s", e)
        if stopping.wait(30.0):
            break


def fills_thread(info: Info, address: str) -> None:
    while not stopping.is_set():
        try:
            fills = info.user_fills(address) or []
            for f in fills:
                tid = f.get("tid")
                if tid is None:
                    continue
                try:
                    tid_i = int(tid)
                except (TypeError, ValueError):
                    continue
                t_ms = f.get("time")
                ts = _to_float(t_ms, time.time() * 1000.0) / 1000.0
                oid = f.get("oid")
                try:
                    oid_i = int(oid) if oid is not None else None
                except (TypeError, ValueError):
                    oid_i = None
                enqueue(
                    "INSERT OR IGNORE INTO fills(tid, ts, oid, side, coin, px, sz, fee, closed_pnl, start_position, dir, hash, raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        tid_i, ts, oid_i,
                        normalize_side(f.get("side")),
                        str(f.get("coin", "")),
                        _to_float(f.get("px"), 0.0) or 0.0,
                        _to_float(f.get("sz"), 0.0) or 0.0,
                        _to_float(f.get("fee")),
                        _to_float(f.get("closedPnl")),
                        _to_float(f.get("startPosition")),
                        str(f.get("dir")) if f.get("dir") is not None else None,
                        str(f.get("hash")) if f.get("hash") is not None else None,
                        json.dumps(f),
                    ),
                )
        except Exception as e:
            log.warning("fills: %s", e)
        if stopping.wait(30.0):
            break


def l2_thread(info: Info, assets: list[str]) -> None:
    while not stopping.is_set():
        for asset in assets:
            if stopping.is_set():
                break
            try:
                snap = info.l2_snapshot(asset)
                levels = (snap or {}).get("levels") or []
                bid = ask = None
                mid = None
                if len(levels) >= 2:
                    bids = levels[0] or []
                    asks = levels[1] or []
                    if bids:
                        bid = _to_float(bids[0].get("px"))
                    if asks:
                        ask = _to_float(asks[0].get("px"))
                    if bid is not None and ask is not None:
                        mid = (bid + ask) / 2.0
                if mid is None and bid is not None:
                    mid = bid
                if mid is None and ask is not None:
                    mid = ask
                if mid is not None:
                    enqueue(
                        "INSERT INTO mids(ts, asset, mid, bid, ask) VALUES(?,?,?,?,?)",
                        (time.time(), asset, mid, bid, ask),
                    )
            except Exception as e:
                log.warning("l2 %s: %s", asset, e)
        if stopping.wait(60.0):
            break


LOG_LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[,.]\d+)?"
    r"\s*(?:-\s*(?P<logger>[\w.]+)\s*)?"
    r"\s*-?\s*(?P<level>DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)?"
    r"\s*[-:]?\s*(?P<msg>.*)$",
    re.IGNORECASE,
)


def ws_watchdog_thread() -> None:
    """Warn if WS callback has been silent too long; WS-only (polling fallback is noisy enough already)."""
    warned = False
    while not stopping.wait(60.0):
        if _last_ws_cb_ts == 0.0:
            continue  # WS never fired once; mids_ws_thread logs its own init errors
        age = time.time() - _last_ws_cb_ts
        if age > 300.0 and not warned:
            log.warning("ws watchdog: no allMids callback in %.0fs (L2 poll still covering)", age)
            warned = True
        elif age <= 300.0 and warned:
            log.info("ws watchdog: callbacks resumed")
            warned = False


def docker_logs_thread(container: str) -> None:
    while not stopping.is_set():
        proc: Optional[subprocess.Popen] = None
        try:
            proc = subprocess.Popen(
                ["docker", "logs", "-f", "--tail", "0", container],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=1, text=True,
            )
            _subprocs.append(proc)
        except Exception as e:
            log.warning("docker logs start failed: %s", e)
            if stopping.wait(10.0):
                break
            continue
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                if stopping.is_set():
                    break
                line = line.rstrip("\n")
                if not line:
                    continue
                m = LOG_LINE_RE.match(line)
                level = None
                msg = line
                if m:
                    level = (m.group("level") or "").upper() or None
                    msg = m.group("msg") or line
                enqueue(
                    "INSERT INTO bot_log(ts, level, message) VALUES(?,?,?)",
                    (time.time(), level, msg),
                )
        except Exception as e:
            log.warning("docker logs stream: %s", e)
        finally:
            try:
                if proc and proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        if stopping.wait(10.0):
            break


def _parse_mem_mb(s: str) -> Optional[float]:
    # e.g. "123.4MiB / 512MiB" -> 123.4 (MB; treat MiB~=MB for research)
    if not s:
        return None
    part = s.split("/")[0].strip()
    m = re.match(r"([0-9.]+)\s*([KMGT]i?B)?", part, re.IGNORECASE)
    if not m:
        return None
    v = _to_float(m.group(1))
    if v is None:
        return None
    unit = (m.group(2) or "MiB").upper()
    if unit.startswith("K"):
        return v / 1024.0
    if unit.startswith("G"):
        return v * 1024.0
    if unit.startswith("T"):
        return v * 1024.0 * 1024.0
    return v


def docker_stats_thread(container: str) -> None:
    while not stopping.is_set():
        try:
            r = subprocess.run(
                ["docker", "stats", "--no-stream", "--format",
                 "{{.CPUPerc}} {{.MemUsage}}", container],
                capture_output=True, text=True, timeout=15,
            )
            out = (r.stdout or "").strip()
            if out:
                parts = out.split(None, 1)
                cpu_s = parts[0].rstrip("%") if parts else ""
                cpu = _to_float(cpu_s)
                mem_mb = _parse_mem_mb(parts[1]) if len(parts) > 1 else None
                enqueue(
                    "INSERT INTO resource_usage(ts, cpu_pct, mem_mb) VALUES(?,?,?)",
                    (time.time(), cpu, mem_mb),
                )
        except Exception as e:
            log.warning("docker stats: %s", e)
        if stopping.wait(60.0):
            break


# ---------------- Main ----------------

def _handle_signal(signum, _frame) -> None:
    log.info("received signal %s, shutting down", signum)
    stopping.set()


def _container_exists(name: str) -> bool:
    try:
        r = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0 and (r.stdout or "").strip() == "true"
    except Exception:
        return False


def summary_counts(db_path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        for t in TABLES:
            try:
                cur = conn.execute(f"SELECT COUNT(*) FROM {t}")
                out[t] = int(cur.fetchone()[0])
            except Exception:
                out[t] = -1
        conn.close()
    except Exception as e:
        log.warning("summary: %s", e)
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Shadow collector for Chainstack Grid Bot testnet trial")
    ap.add_argument("--address", help="HL account address (default: derive from env private key)")
    ap.add_argument("--out", help="SQLite DB path (default: evaluations/chainstack-grid-bot/shadow/trial-<UTC>.db)")
    ap.add_argument("--assets", default="BTC", help="Comma-separated assets to watch (default: BTC)")
    ap.add_argument("--bot-container", default=DEFAULT_CONTAINER, help="Docker container name")
    ap.add_argument("--no-docker-logs", action="store_true", help="Disable docker log tailing")
    ap.add_argument("--no-docker-stats", action="store_true", help="Disable docker stats polling")
    ap.add_argument("--verbose", action="store_true", help="DEBUG logging")
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    load_dotenv(PROJECT_ROOT / ".env")

    if args.address:
        address = args.address
    else:
        address = derive_address_from_env()

    assets = [a.strip() for a in args.assets.split(",") if a.strip()]
    if not assets:
        log.error("no assets specified")
        return 2

    if args.out:
        db_path = Path(args.out)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
        db_path = PROJECT_ROOT / "evaluations" / "chainstack-grid-bot" / "shadow" / f"trial-{stamp}.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"shadow_collector v{COLLECTOR_VERSION}")
    print(f"address: {address[:6]}...{address[-4:]}")
    print(f"db:      {db_path}")
    print(f"assets:  {','.join(assets)}")
    print(f"container: {args.bot_container}")

    # Validate HL connectivity up front.
    try:
        info = Info(TESTNET_API_URL, skip_ws=True, spot_meta={"universe": [], "tokens": []})
        _ = info.all_mids()
    except Exception as e:
        log.error("initial HL connection failed: %s", e)
        return 2

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Start writer first.
    w = threading.Thread(target=writer_thread, args=(db_path,), name="writer", daemon=True)
    w.start()

    insert_meta("started_at", str(time.time()))
    insert_meta("address", address)
    insert_meta("assets", ",".join(assets))
    insert_meta("collector_version", COLLECTOR_VERSION)
    insert_meta("bot_container", args.bot_container)

    threads: list[threading.Thread] = []
    threads.append(threading.Thread(target=mids_ws_thread, args=(assets,), name="mids", daemon=True))
    threads.append(threading.Thread(target=ws_watchdog_thread, name="ws_watchdog", daemon=True))
    threads.append(threading.Thread(target=account_thread, args=(info, address), name="account", daemon=True))
    threads.append(threading.Thread(target=orders_thread, args=(info, address), name="orders", daemon=True))
    threads.append(threading.Thread(target=fills_thread, args=(info, address), name="fills", daemon=True))
    threads.append(threading.Thread(target=l2_thread, args=(info, assets), name="l2", daemon=True))

    if not args.no_docker_logs:
        if _container_exists(args.bot_container):
            threads.append(threading.Thread(
                target=docker_logs_thread, args=(args.bot_container,), name="docker_logs", daemon=True))
        else:
            log.info("container %s not found; skipping log tailing", args.bot_container)
    if not args.no_docker_stats:
        if _container_exists(args.bot_container):
            threads.append(threading.Thread(
                target=docker_stats_thread, args=(args.bot_container,), name="docker_stats", daemon=True))
        else:
            log.info("container %s not found; skipping stats", args.bot_container)

    for t in threads:
        t.start()

    log.info("collector running (%d workers); Ctrl-C to stop", len(threads))
    while not stopping.is_set():
        time.sleep(0.5)

    log.info("shutting down; waiting up to 10s for workers")
    # Unblock any subprocesses blocked on stdout.
    for sp in list(_subprocs):
        try:
            if sp.poll() is None:
                sp.terminate()
        except Exception:
            pass
    deadline = time.time() + 10.0
    for t in threads:
        remaining = max(0.1, deadline - time.time())
        t.join(timeout=remaining)

    # Signal writer to drain + exit (sentinel pushed AFTER workers joined).
    write_q.put(None)
    w.join(timeout=10.0)

    counts = summary_counts(db_path)
    print("summary (rows per table):")
    for t in TABLES:
        print(f"  {t}: {counts.get(t, -1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
