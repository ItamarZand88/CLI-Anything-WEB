#!/usr/bin/env python3
"""Capture HTTP traffic via mitmproxy proxy + Playwright browser.

Replaces the parse-trace.py workflow with real-time traffic interception.
Outputs raw-traffic.json in the same schema as parse-trace.py for backward
compatibility with analyze-traffic.py and Phase 2 methodology.

Improvements over trace-based capture:
- No response body truncation (full bodies for all content types)
- Real-time noise filtering (skip analytics/tracking during capture)
- Request sequencing with precise timestamps
- Cookie jar evolution tracking (Set-Cookie headers)
- Request deduplication
- Direct Python objects — no trace zip parsing or SHA1 hash lookups

Usage:
    # All-in-one mode (original behavior, default):
    python mitmproxy-capture.py capture <url> --output raw-traffic.json
    python mitmproxy-capture.py <url> --output raw-traffic.json          # backward compat

    # Start/stop proxy mode (agent-driven):
    python mitmproxy-capture.py start-proxy --port 8080
    # ... agent browses with: npx playwright-cli open <url> --proxy=http://127.0.0.1:8080
    python mitmproxy-capture.py stop-proxy -o raw-traffic.json

Requirements:
    pip install mitmproxy playwright
"""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows event-loop fix (must be before any async imports touch the loop)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

from mitmproxy import options as mopt, http  # noqa: E402
from mitmproxy.tools.dump import DumpMaster  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Ensure sibling modules resolve whether invoked as a script or via importlib.
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from traffic_utils import NOISE_PATTERNS, STATIC_EXTENSIONS  # noqa: E402,F401
from traffic_utils import is_noise_url as _is_noise  # noqa: E402
from traffic_utils import is_static_asset as _is_static  # noqa: E402


# ---------------------------------------------------------------------------
# mitmproxy Addon — captures traffic into a list
# ---------------------------------------------------------------------------

class TrafficRecorder:
    """mitmproxy addon that records HTTP request/response pairs.

    Outputs entries in the same schema as parse-trace.py for backward
    compatibility with analyze-traffic.py.
    """

    # MIME types that are never useful for CLI generation
    SKIP_MIMES = frozenset((
        "image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml",
        "image/avif", "image/x-icon", "image/bmp", "image/tiff",
        "font/woff", "font/woff2", "font/ttf", "font/otf",
        "application/font-woff", "application/font-woff2",
        "video/mp4", "video/webm", "audio/mpeg", "audio/ogg",
        "application/octet-stream",
    ))

    def __init__(self, *, filter_static: bool = True, filter_noise: bool = True,
                 dedup: bool = True, max_body_bytes: int = 0):
        self.entries: list[dict] = []
        self._lock = threading.Lock()
        self.filter_static = filter_static
        self.filter_noise = filter_noise
        self.dedup = dedup
        self.max_body_bytes = max_body_bytes  # 0 = unlimited
        self._seen: set[str] = set()  # for dedup
        self._stats = {"total_seen": 0, "filtered_static": 0,
                       "filtered_noise": 0, "deduped": 0, "captured": 0}

    def response(self, flow: http.HTTPFlow) -> None:
        """Called when a full response has been received."""
        url = flow.request.url
        self._stats["total_seen"] += 1

        # Real-time filtering
        if self.filter_static and _is_static(url):
            self._stats["filtered_static"] += 1
            return

        if self.filter_noise and _is_noise(url):
            self._stats["filtered_noise"] += 1
            return

        # Filter by response MIME type (catches images/fonts from CDN URLs)
        if self.filter_static and flow.response:
            ct = flow.response.headers.get("content-type", "").split(";")[0].strip().lower()
            if ct in self.SKIP_MIMES:
                self._stats["filtered_static"] += 1
                return

        # Deduplication: same method + URL + body hash
        if self.dedup:
            body_sig = ""
            if flow.request.content:
                body_sig = str(hash(flow.request.content))
            dedup_key = f"{flow.request.method}|{url}|{body_sig}"
            if dedup_key in self._seen:
                self._stats["deduped"] += 1
                return
            self._seen.add(dedup_key)

        # Extract request body
        post_data = None
        if flow.request.content and flow.request.method in ("POST", "PUT", "PATCH", "DELETE"):
            try:
                post_data = flow.request.get_text()
            except (ValueError, UnicodeDecodeError):
                post_data = f"[binary {len(flow.request.content)} bytes]"

        # Extract response body — NO TRUNCATION (key improvement)
        response_body = None
        if flow.response and flow.response.content:
            ct = flow.response.headers.get("content-type", "")
            body_bytes = flow.response.content

            # Respect max_body_bytes if set
            if self.max_body_bytes and len(body_bytes) > self.max_body_bytes:
                response_body = f"[large response {len(body_bytes)} bytes]"
            elif "json" in ct or "javascript" in ct:
                try:
                    response_body = json.loads(body_bytes)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        response_body = body_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        response_body = f"[binary {len(body_bytes)} bytes]"
            elif "text" in ct or "html" in ct or "xml" in ct:
                try:
                    response_body = body_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    response_body = f"[binary {len(body_bytes)} bytes]"
            else:
                response_body = f"[binary {len(body_bytes)} bytes]"

        # Compute timing
        time_ms = 0.0
        if flow.response and flow.response.timestamp_end and flow.request.timestamp_start:
            time_ms = round(
                (flow.response.timestamp_end - flow.request.timestamp_start) * 1000, 1
            )

        # Build entry — backward-compatible with parse-trace.py schema
        entry = {
            "url": url,
            "method": flow.request.method,
            "request_headers": dict(flow.request.headers),
            "post_data": post_data,
            "status": flow.response.status_code if flow.response else 0,
            "response_headers": dict(flow.response.headers) if flow.response else {},
            "response_body": response_body,
            "mime_type": (
                flow.response.headers.get("content-type", "").split(";")[0].strip()
                if flow.response else ""
            ),
            "time_ms": time_ms,
            # --- Enhanced fields (new, ignored by analyze-traffic.py) ---
            "timestamp": flow.request.timestamp_start,
            "request_cookies": dict(flow.request.cookies) if flow.request.cookies else {},
            "response_cookies": self._extract_set_cookies(flow),
            "request_body_size": len(flow.request.content) if flow.request.content else 0,
            "response_body_size": len(flow.response.content) if flow.response and flow.response.content else 0,
            "http_version": flow.request.http_version,
        }

        with self._lock:
            self.entries.append(entry)
        self._stats["captured"] += 1

    def error(self, flow: http.HTTPFlow) -> None:
        """Called when a flow error occurs (connection reset, timeout, etc.)."""
        with self._lock:
            self.entries.append({
                "url": flow.request.url,
                "method": flow.request.method,
                "request_headers": dict(flow.request.headers),
                "post_data": None,
                "status": 0,
                "response_headers": {},
                "response_body": None,
                "mime_type": "",
                "time_ms": 0,
                "error": str(flow.error) if flow.error else "unknown error",
                "timestamp": flow.request.timestamp_start,
            })

    @staticmethod
    def _extract_set_cookies(flow: http.HTTPFlow) -> list[dict]:
        """Extract Set-Cookie headers into structured format."""
        if not flow.response:
            return []
        cookies = []
        for name, value in flow.response.cookies.items():
            cookies.append({"name": name, "value": value})
        return cookies

    @property
    def stats(self) -> dict:
        return {**self._stats}

    def snapshot(self) -> list[dict]:
        """Return a thread-safe copy of all captured entries."""
        with self._lock:
            return list(self.entries)

    def reset(self) -> None:
        """Clear all captured entries, dedup set, and stats."""
        with self._lock:
            self.entries.clear()
        self._seen.clear()
        self._stats = {"total_seen": 0, "filtered_static": 0,
                       "filtered_noise": 0, "deduped": 0, "captured": 0}


# ---------------------------------------------------------------------------
# Proxy lifecycle — start/stop mitmproxy in a background thread
# ---------------------------------------------------------------------------

class ProxyManager:
    """Manages mitmproxy DumpMaster in a background thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, **recorder_kwargs):
        self.host = host
        self.port = port
        self.recorder = TrafficRecorder(**recorder_kwargs)
        self._master: DumpMaster | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the proxy in a background thread."""
        self._loop = asyncio.new_event_loop()
        self._ready = threading.Event()
        self._error: str | None = None

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="mitmproxy-capture",
        )
        self._thread.start()

        # Wait until proxy signals ready or error
        if not self._ready.wait(timeout=15):
            raise RuntimeError(f"mitmproxy failed to start on {self.host}:{self.port} (timeout)")
        if self._error:
            raise RuntimeError(self._error)

        # Restore default event loop policy for main thread.
        # mitmproxy sets WindowsSelectorEventLoopPolicy globally, but
        # Playwright needs ProactorEventLoop for subprocess support.
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    def _run(self) -> None:
        """Run the proxy event loop (called in background thread)."""
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_run())

    async def _async_run(self) -> None:
        """Create and run DumpMaster inside the async context (required by mitmproxy)."""
        try:
            opts = mopt.Options(
                listen_host=self.host,
                listen_port=self.port,
                ssl_insecure=True,
            )
            # DumpMaster must be created inside a running event loop
            self._master = DumpMaster(opts, with_termlog=False, with_dumper=False)
            self._master.addons.add(self.recorder)
            self._ready.set()
            await self._master.run()
        except Exception as e:
            self._error = str(e)
            self._ready.set()

    def stop(self) -> None:
        """Shutdown the proxy gracefully."""
        if self._master:
            self._master.shutdown()
        if self._thread:
            self._thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Browser session — launch Playwright through the proxy
# ---------------------------------------------------------------------------

def run_browser_session(url: str, proxy_port: int, *, headless: bool = False,
                        timeout: int = 0) -> None:
    """Launch a Playwright browser pointed at the mitmproxy proxy.

    If timeout > 0, auto-closes after that many seconds.
    If timeout == 0, waits for user to press Enter.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
            proxy={"server": f"http://127.0.0.1:{proxy_port}"},
        )
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"  Navigating to {url} ...")
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        print(f"  Page loaded. Browser is live.")

        if timeout > 0:
            print(f"  Auto-closing in {timeout}s. Interact with the page now.")
            time.sleep(timeout)
        else:
            print("  Browse the site to capture traffic.")
            print("  Press Enter here when done...")
            try:
                input()
            except EOFError:
                # Running non-interactively (e.g., from agent)
                print("  Non-interactive mode. Waiting 10s for traffic...")
                time.sleep(10)

        browser.close()


# ---------------------------------------------------------------------------
# Site fingerprint — quick assessment via Playwright (no proxy needed)
# ---------------------------------------------------------------------------

def run_fingerprint(url: str, proxy_port: int) -> dict | None:
    """Run site fingerprint via the proxy to detect framework/protection.

    site-fingerprint.js is a playwright run-code callback (``async page => {...}``).
    We can't use ``page.evaluate()`` with it directly because that runs in the
    browser context. Instead we inline the browser-side evaluation here.
    """
    from playwright.sync_api import sync_playwright

    # Browser-context JS that collects site fingerprint data.
    # This is the same logic as site-fingerprint.js but as a plain expression.
    FINGERPRINT_EVAL = """(() => {
        try {
            const body = document.body ? document.body.textContent.toLowerCase() : "";
            const html = document.documentElement ? document.documentElement.outerHTML : "";
            const scripts = Array.from(document.querySelectorAll("script[src]")).map(s => s.src);
            return {
                framework: {
                    nextPages: !!document.getElementById("__NEXT_DATA__"),
                    nextApp: html.includes("self.__next_f.push"),
                    nuxt: typeof window.__NUXT__ !== "undefined",
                    remix: typeof window.__remixContext !== "undefined",
                    gatsby: typeof window.___gatsby !== "undefined",
                    sveltekit: typeof window.__sveltekit_data !== "undefined",
                    googleBatch: typeof window.WIZ_global_data !== "undefined",
                    angular: !!document.querySelector("[ng-version]"),
                    react: !!document.querySelector("[data-reactroot]"),
                    spaRoot: (document.querySelector("#app, #root, #__next, #__nuxt") || {}).id || null,
                    preloadedState: typeof window.__INITIAL_STATE__ !== "undefined" ||
                                    typeof window.__PRELOADED_STATE__ !== "undefined"
                },
                protection: {
                    cloudflare: html.includes("cf-ray") || html.includes("__cf_bm"),
                    captcha: !!(document.querySelector(".g-recaptcha") ||
                               document.querySelector("#px-captcha") ||
                               document.querySelector(".h-captcha")),
                    akamai: scripts.some(s => s.includes("akamai")),
                    datadome: scripts.some(s => s.includes("datadome")),
                    perimeterx: scripts.some(s => s.includes("perimeterx") || s.includes("/px/")),
                    awsWaf: html.includes("aws-waf-token") || body.includes("automated access"),
                    serviceWorker: !!(navigator.serviceWorker && navigator.serviceWorker.controller)
                },
                auth: {
                    hasLoginButton: body.includes("sign in") || body.includes("log in") || body.includes("sign up"),
                    hasUserMenu: !!document.querySelector(
                        "[aria-label*=account], [aria-label*=profile], .user-menu, .avatar"
                    ),
                    hasAuthMeta: !!document.querySelector("meta[name=csrf-token], meta[name=_token]")
                },
                page: {
                    title: document.title,
                    url: location.href,
                    lang: document.documentElement ? document.documentElement.lang : null,
                    scripts: scripts.slice(0, 15)
                }
            };
        } catch (e) {
            return { error: e.message };
        }
    })()"""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": f"http://127.0.0.1:{proxy_port}"},
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            result = page.evaluate(FINGERPRINT_EVAL)
            browser.close()
            return result
        except Exception as e:
            browser.close()
            print(f"  Fingerprint failed: {e}", file=sys.stderr)
            return None


# ---------------------------------------------------------------------------
# Output — write raw-traffic.json + auto-run analysis
# ---------------------------------------------------------------------------

def write_output(entries: list[dict], output_path: Path, stats: dict) -> None:
    """Write captured traffic to JSON and auto-run analysis."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(entries, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n  Captured {stats['captured']} API requests -> {output_path}")
    print(f"  (filtered: {stats['filtered_static']} static, "
          f"{stats['filtered_noise']} noise, {stats['deduped']} dupes "
          f"of {stats['total_seen']} total)")

    # Auto-run analysis (same as parse-trace.py)
    if not entries:
        return

    analysis_path = output_path.parent / "traffic-analysis.json"
    analyze_script = Path(__file__).parent / "analyze-traffic.py"
    if analyze_script.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("analyze_traffic", analyze_script)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            report = mod.analyze(entries)
            analysis_path.write_text(
                json.dumps(report, indent=2, default=str),
                encoding="utf-8",
            )
            p = report["protocol"]
            a = report["auth"]
            s = report["stats"]
            print(f"  Analysis: protocol={p['protocol']} ({p['confidence']}%), "
                  f"auth={a['primary']}, "
                  f"requests={s['total_requests']} ({s['read_operations']}R/{s['write_operations']}W)")
            if p.get("graphql_operations"):
                ops = [op["name"] for op in p["graphql_operations"]]
                print(f"    GraphQL ops: {', '.join(ops)}")
            if p.get("batchexecute_rpc_ids"):
                print(f"    batchexecute IDs: {', '.join(p['batchexecute_rpc_ids'])}")
            print(f"    -> {analysis_path}")
        except Exception as e:
            print(f"  (analysis skipped: {e})", file=sys.stderr)


# ---------------------------------------------------------------------------
# State file helpers for start-proxy / stop-proxy mode
# ---------------------------------------------------------------------------

def _state_file_path(port: int = 0) -> Path:
    """State file namespaced by port for parallel session support."""
    suffix = f"-{port}" if port else ""
    return Path.cwd() / f".mitmproxy-capture{suffix}.state.json"


def _stop_signal_path(port: int = 0) -> Path:
    """Stop signal file namespaced by port for parallel session support."""
    suffix = f"-{port}" if port else ""
    return Path.cwd() / f".mitmproxy-capture{suffix}.stop"


def _read_state(port: int = 0) -> dict | None:
    """Read the state file. Returns None if missing or stale.

    If port=0, searches for any .mitmproxy-capture*.state.json in cwd.
    """
    if port:
        candidates = [_state_file_path(port)]
    else:
        # Find any state file in cwd
        candidates = sorted(Path.cwd().glob(".mitmproxy-capture*.state.json"))

    for sf in candidates:
        if not sf.exists():
            continue
        try:
            state = json.loads(sf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        # Check if the process is still alive
        pid = state.get("pid")
        if pid and not _is_pid_alive(pid):
            # Stale state file — clean up
            sf.unlink(missing_ok=True)
            continue
        # Store which file we found (for cleanup)
        state["_state_file"] = str(sf)
        return state
    return None


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with given PID is alive (cross-platform)."""
    if sys.platform == "win32":
        # Use tasklist on Windows
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False


def _cleanup_state_files(port: int = 0) -> None:
    """Remove state and signal files for the given port."""
    _state_file_path(port).unlink(missing_ok=True)
    _stop_signal_path(port).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Daemon mode — runs as a background process for start-proxy
# ---------------------------------------------------------------------------

def _run_daemon(port: int, traffic_file: str, **recorder_kwargs) -> None:
    """Run the proxy as a long-lived daemon process.

    Polls for a stop signal file. When the signal file appears, writes
    captured traffic to the output path specified in the signal file,
    then exits cleanly.
    """
    print(f"mitmproxy-capture daemon starting on 127.0.0.1:{port}")
    print(f"  Traffic buffer: {traffic_file}")

    proxy = ProxyManager(port=port, **recorder_kwargs)
    try:
        proxy.start()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        _cleanup_state_files(port)
        sys.exit(1)

    print(f"  Proxy ready. Waiting for stop signal...")

    # Poll for stop signal file
    stop_path = _stop_signal_path(port)
    try:
        while True:
            if stop_path.exists():
                try:
                    signal_data = json.loads(stop_path.read_text(encoding="utf-8"))
                    output_path = signal_data.get("output", traffic_file)
                except (json.JSONDecodeError, OSError):
                    output_path = traffic_file
                break
            if not proxy._thread.is_alive():
                print("  Proxy thread died unexpectedly. Flushing traffic and exiting.", file=sys.stderr)
                _flush_traffic(proxy.recorder.snapshot(), Path(traffic_file))
                break
            # Periodically flush traffic to disk as a safety measure
            _flush_traffic(proxy.recorder.snapshot(), Path(traffic_file))
            time.sleep(0.5)
    except KeyboardInterrupt:
        output_path = traffic_file

    # Stop proxy and write final output
    proxy.stop()

    entries = sorted(
        proxy.recorder.snapshot(),
        key=lambda e: e.get("timestamp", 0) or 0,
    )

    write_output(entries, Path(output_path), proxy.recorder.stats)
    _cleanup_state_files(port)
    print("  Daemon exiting.")


def _flush_traffic(entries: list[dict], path: Path) -> None:
    """Write current traffic buffer to disk (incremental safety flush)."""
    if not entries:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(entries, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass  # Best-effort flush


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_start_proxy(args) -> None:
    """Start the proxy as a background daemon process."""
    port = args.port

    # Check for existing proxy on this port
    existing = _read_state(port)
    if existing:
        print(f"Error: Proxy already running (PID {existing['pid']}) on port {existing['port']}.",
              file=sys.stderr)
        print(f"  Run 'stop-proxy' first, or delete {_state_file_path(port)} if stale.", file=sys.stderr)
        sys.exit(1)
    import tempfile
    fd, traffic_file = tempfile.mkstemp(prefix="mitmproxy-traffic-", suffix=".json")
    os.close(fd)  # Close the fd, we'll write via Path

    # Build daemon command — re-invoke ourselves with --_daemon flag
    daemon_cmd = [
        sys.executable, __file__, "--_daemon",
        "--port", str(port),
        "--traffic-file", traffic_file,
    ]
    if args.include_static:
        daemon_cmd.append("--include-static")
    if args.include_noise:
        daemon_cmd.append("--include-noise")
    if args.no_dedup:
        daemon_cmd.append("--no-dedup")
    if args.max_body:
        daemon_cmd.extend(["--max-body", str(args.max_body)])

    # Start daemon as a detached subprocess
    log_file = Path(traffic_file).with_suffix(".log")
    log_fh = open(log_file, "w")

    if sys.platform == "win32":
        # Windows: use CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        creation_flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
        proc = subprocess.Popen(
            daemon_cmd,
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=log_fh,
            stdin=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            daemon_cmd,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=log_fh,
            stdin=subprocess.DEVNULL,
        )

    # Write state file
    state = {
        "pid": proc.pid,
        "port": port,
        "traffic_file": traffic_file,
        "log_file": str(log_file),
        "started_at": time.time(),
    }
    _state_file_path(port).write_text(
        json.dumps(state, indent=2),
        encoding="utf-8",
    )

    # Wait briefly to see if daemon started successfully
    time.sleep(2)
    if proc.poll() is not None:
        print(f"Error: Daemon process exited immediately (exit code {proc.returncode}).",
              file=sys.stderr)
        _cleanup_state_files(port)
        sys.exit(1)

    # Verify the proxy is actually listening on the port
    import socket
    proxy_ready = False
    for _ in range(20):  # Try for up to 10 seconds
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(("127.0.0.1", port))
            proxy_ready = True
            break
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)

    if not proxy_ready:
        print(f"Error: Proxy process started (PID {proc.pid}) but is not listening on port {port}.",
              file=sys.stderr)
        print(f"  The daemon may have failed to initialize mitmproxy.", file=sys.stderr)
        _cleanup_state_files(port)
        try:
            proc.kill()
        except OSError:
            pass
        sys.exit(1)

    print(f"mitmproxy-capture v1.0.0 — proxy started")
    print(f"  PID:   {proc.pid}")
    print(f"  Proxy: http://127.0.0.1:{port}")
    print(f"  State: {_state_file_path(port)}")
    print(f"")
    print(f"  Use this proxy URL with your browser:")
    print(f"    npx @playwright/cli@latest open <url> --proxy-server=http://127.0.0.1:{port} --ignore-https-errors")
    print(f"")
    print(f"  When done, run:")
    print(f"    python {Path(__file__).name} stop-proxy -o raw-traffic.json")


def cmd_stop_proxy(args) -> None:
    """Stop the running proxy daemon and write captured traffic."""
    # Try port-specific state first, then any state file
    port_hint = getattr(args, "port", 0)
    state = _read_state(port_hint)
    if not state:
        print(f"Error: No running proxy found. No state file in {Path.cwd()}.",
              file=sys.stderr)
        sys.exit(1)

    pid = state["pid"]
    port = state["port"]
    traffic_file = state["traffic_file"]
    output_path = args.output

    print(f"mitmproxy-capture v1.0.0 — stopping proxy")
    print(f"  PID:    {pid}")
    print(f"  Port:   {port}")
    print(f"  Output: {output_path}")

    # Create stop signal file with desired output path
    _stop_signal_path(port).write_text(
        json.dumps({"output": str(Path(output_path).resolve())}),
        encoding="utf-8",
    )

    # Wait for daemon to write output and exit
    print(f"  Waiting for daemon to flush traffic...")
    deadline = time.time() + 30  # 30s timeout
    while time.time() < deadline:
        if not _is_pid_alive(pid):
            break
        time.sleep(0.5)
    else:
        print(f"  Warning: Daemon did not exit within 30s. Killing PID {pid}...",
              file=sys.stderr)
        _force_kill(pid)

    # Check if output was written by the daemon
    out = Path(output_path).resolve()
    if out.exists():
        try:
            entries = json.loads(out.read_text(encoding="utf-8"))
            print(f"  Done. {len(entries)} requests captured -> {output_path}")
        except (json.JSONDecodeError, OSError):
            print(f"  Done. Output written to {output_path}")
    else:
        # Daemon might have written to traffic_file instead; copy it
        tf = Path(traffic_file)
        if tf.exists():
            import shutil
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tf, out)
            try:
                entries = json.loads(out.read_text(encoding="utf-8"))
                print(f"  Done. {len(entries)} requests captured -> {output_path}")
            except (json.JSONDecodeError, OSError):
                print(f"  Done. Output written to {output_path}")
            tf.unlink(missing_ok=True)
        else:
            print(f"  Warning: No traffic data found. The proxy may not have captured any requests.",
                  file=sys.stderr)

    # Check daemon log for errors
    log_file = state.get("log_file")
    if log_file:
        lf = Path(log_file)
        if lf.exists():
            log_content = lf.read_text(encoding="utf-8", errors="replace").strip()
            if log_content:
                print(f"\n  Daemon log ({lf}):")
                for line in log_content.splitlines()[-20:]:
                    print(f"    {line}")
            lf.unlink(missing_ok=True)

    _cleanup_state_files(port)


def _force_kill(pid: int) -> None:
    """Force-kill a process by PID (cross-platform)."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=5)
        else:
            os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, subprocess.TimeoutExpired):
        pass


def cmd_capture(args) -> None:
    """All-in-one capture mode (original behavior)."""
    print(f"mitmproxy-capture v1.0.0")
    print(f"  Target: {args.url}")
    print(f"  Proxy:  127.0.0.1:{args.port}")

    # Start proxy
    print(f"  Starting mitmproxy proxy...")
    proxy = ProxyManager(
        port=args.port,
        filter_static=not args.include_static,
        filter_noise=not args.include_noise,
        dedup=not args.no_dedup,
        max_body_bytes=args.max_body,
    )
    try:
        proxy.start()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        print(f"  Is port {args.port} already in use? Try --port <other>", file=sys.stderr)
        sys.exit(1)

    print(f"  Proxy ready.")

    # Optional fingerprint
    if args.fingerprint:
        print(f"  Running site fingerprint...")
        fp = run_fingerprint(args.url, args.port)
        if fp:
            fp_path = Path(args.output).parent / "fingerprint.json"
            fp_path.write_text(json.dumps(fp, indent=2, default=str), encoding="utf-8")
            print(f"    Framework: {fp.get('framework', 'unknown')}")
            print(f"    Protection: {fp.get('protection', 'none')}")
            print(f"    -> {fp_path}")

        # Clear fingerprint traffic so it doesn't pollute the real capture
        proxy.recorder.reset()

    # Run browser session (interactive or timed)
    try:
        run_browser_session(
            args.url,
            args.port,
            headless=args.headless,
            timeout=args.timeout,
        )
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    except Exception as e:
        print(f"  Browser error: {e}", file=sys.stderr)

    # Stop proxy and write output
    proxy.stop()

    # Sort entries by timestamp for sequence analysis
    entries = sorted(
        proxy.recorder.snapshot(),
        key=lambda e: e.get("timestamp", 0) or 0,
    )

    write_output(entries, Path(args.output), proxy.recorder.stats)


# ---------------------------------------------------------------------------
# Shared argument helpers
# ---------------------------------------------------------------------------

def _add_filter_args(parser: argparse.ArgumentParser) -> None:
    """Add common filtering arguments to a parser."""
    parser.add_argument(
        "--include-static", action="store_true",
        help="Include static assets (JS, CSS, images) — filtered by default",
    )
    parser.add_argument(
        "--include-noise", action="store_true",
        help="Include analytics/tracking requests — filtered by default",
    )
    parser.add_argument(
        "--no-dedup", action="store_true",
        help="Disable request deduplication",
    )
    parser.add_argument(
        "--max-body", type=int, default=0,
        help="Max response body size in bytes (0 = unlimited)",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Capture HTTP traffic via mitmproxy proxy",
    )
    # Hidden flag for daemon mode (re-invoked by start-proxy)
    parser.add_argument("--_daemon", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--traffic-file", help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command")

    # --- capture (all-in-one, original mode) ---
    cap = subparsers.add_parser(
        "capture", help="All-in-one: start proxy, open browser, capture, write output",
    )
    cap.add_argument("url", help="URL to open in the browser")
    cap.add_argument(
        "--output", "-o", default="raw-traffic.json",
        help="Output file path (default: raw-traffic.json)",
    )
    cap.add_argument(
        "--port", "-p", type=int, default=8080,
        help="Proxy port (default: 8080)",
    )
    _add_filter_args(cap)
    cap.add_argument(
        "--headless", action="store_true",
        help="Run browser in headless mode",
    )
    cap.add_argument(
        "--timeout", "-t", type=int, default=0,
        help="Auto-close browser after N seconds (0 = wait for Enter)",
    )
    cap.add_argument(
        "--fingerprint", action="store_true",
        help="Run site fingerprint before capture",
    )

    # --- start-proxy ---
    sp = subparsers.add_parser(
        "start-proxy", help="Start proxy daemon in background (agent browses separately)",
    )
    sp.add_argument(
        "--port", "-p", type=int, default=8080,
        help="Proxy port (default: 8080)",
    )
    _add_filter_args(sp)

    # --- stop-proxy ---
    stp = subparsers.add_parser(
        "stop-proxy", help="Stop proxy daemon and write captured traffic",
    )
    stp.add_argument(
        "--output", "-o", default="raw-traffic.json",
        help="Output file path (default: raw-traffic.json)",
    )
    stp.add_argument(
        "--port", "-p", type=int, default=0,
        help="Port of the proxy to stop (default: auto-detect from state file)",
    )

    # --- Detect mode before parsing ---
    # Check for daemon mode first (internal flag)
    if "--_daemon" in sys.argv:
        daemon_parser = argparse.ArgumentParser()
        daemon_parser.add_argument("--_daemon", action="store_true")
        daemon_parser.add_argument("--port", "-p", type=int, default=8080)
        daemon_parser.add_argument("--traffic-file", required=True)
        _add_filter_args(daemon_parser)
        dargs = daemon_parser.parse_args()
        _run_daemon(
            port=dargs.port,
            traffic_file=dargs.traffic_file,
            filter_static=not dargs.include_static,
            filter_noise=not dargs.include_noise,
            dedup=not dargs.no_dedup,
            max_body_bytes=dargs.max_body,
        )
        return

    # Backward compatibility: if first positional arg looks like a URL
    # (not a known subcommand), treat as legacy `capture <url>` invocation.
    known_commands = {"capture", "start-proxy", "stop-proxy", "--help", "-h"}
    first_positional = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            first_positional = arg
            break

    if first_positional and first_positional not in known_commands:
        # Legacy mode: python mitmproxy-capture.py <url> [options]
        compat_parser = argparse.ArgumentParser(
            description="Capture HTTP traffic via mitmproxy + Playwright"
        )
        compat_parser.add_argument("url", help="URL to open in the browser")
        compat_parser.add_argument(
            "--output", "-o", default="raw-traffic.json",
            help="Output file path (default: raw-traffic.json)",
        )
        compat_parser.add_argument(
            "--port", "-p", type=int, default=8080,
            help="Proxy port (default: 8080)",
        )
        _add_filter_args(compat_parser)
        compat_parser.add_argument("--headless", action="store_true")
        compat_parser.add_argument("--timeout", "-t", type=int, default=0)
        compat_parser.add_argument("--fingerprint", action="store_true")
        compat_args = compat_parser.parse_args()
        cmd_capture(compat_args)
        return

    args = parser.parse_args()

    if args.command == "capture":
        cmd_capture(args)
    elif args.command == "start-proxy":
        cmd_start_proxy(args)
    elif args.command == "stop-proxy":
        cmd_stop_proxy(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
