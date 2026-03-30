"""HTTP client for ChatGPT backend API.

Hybrid approach:
- curl_cffi for read-only endpoints (conversations, models, me, images)
- Playwright headless browser for chat/image generation (handles sentinel anti-abuse)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from curl_cffi import requests as curl_requests

from .auth import load_auth, CONFIG_DIR
from .exceptions import (
    AuthError,
    ChatGPTError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
)

BASE_URL = "https://chatgpt.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
)


class ChatGPTClient:
    """Client for ChatGPT's backend REST API."""

    def __init__(self) -> None:
        self._auth: dict[str, Any] | None = None
        self._session = curl_requests.Session(
            impersonate="chrome131",
            timeout=60,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> ChatGPTClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _load_auth(self) -> dict[str, Any]:
        if self._auth is None:
            self._auth = load_auth()
        return self._auth

    def _headers(self) -> dict[str, str]:
        auth = self._load_auth()
        headers = {
            "Authorization": f"Bearer {auth['access_token']}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "oai-device-id": auth.get("device_id", ""),
            "oai-language": "en-US",
        }
        return headers

    def _cookies(self) -> dict[str, str]:
        auth = self._load_auth()
        return auth.get("cookies", {})

    def _check_response(self, resp, path: str) -> None:
        if resp.status_code == 401 or resp.status_code == 403:
            raise AuthError(
                f"Authentication failed ({resp.status_code}). Run: cli-web-chatgpt auth login",
                recoverable=False,
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {path}")
        if resp.status_code == 429:
            retry = resp.headers.get("retry-after")
            raise RateLimitError(
                "Rate limited by ChatGPT",
                retry_after=float(retry) if retry else None,
            )
        if resp.status_code >= 500:
            raise ServerError(
                f"Server error {resp.status_code}", status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise ChatGPTError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{BASE_URL}{path}"
        try:
            resp = self._session.get(
                url,
                headers=self._headers(),
                cookies=self._cookies(),
                params=params,
            )
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc

        self._check_response(resp, path)
        return resp.json()

    def _post(self, path: str, data: dict | None = None, extra_headers: dict | None = None) -> Any:
        url = f"{BASE_URL}{path}"
        headers = self._headers()
        if extra_headers:
            headers.update(extra_headers)
        try:
            resp = self._session.post(
                url,
                headers=headers,
                cookies=self._cookies(),
                json=data or {},
            )
        except Exception as exc:
            raise NetworkError(f"Request failed: {exc}") from exc

        self._check_response(resp, path)
        return resp.json()

    # ── API Methods ─────────────────────────────────────────────

    def get_me(self) -> dict:
        return self._get("/backend-api/me")

    def get_models(self) -> list[dict]:
        data = self._get("/backend-api/models", params={"iim": "false", "is_gizmo": "false"})
        return data.get("models", [])

    def list_conversations(
        self,
        limit: int = 28,
        offset: int = 0,
        archived: bool = False,
        starred: bool = False,
    ) -> dict:
        params = {
            "offset": offset,
            "limit": limit,
            "order": "updated",
            "is_archived": str(archived).lower(),
            "is_starred": str(starred).lower(),
        }
        return self._get("/backend-api/conversations", params=params)

    def get_conversation(self, conversation_id: str) -> dict:
        return self._get(f"/backend-api/conversation/{conversation_id}")

    def list_recent_images(self, limit: int = 25) -> dict:
        return self._get("/backend-api/my/recent/image_gen", params={"limit": limit})

    def get_image_styles(self) -> dict:
        return self._get("/backend-api/images/styles")

    def get_file_download_url(self, file_id: str, conversation_id: str) -> dict:
        return self._get(
            f"/backend-api/files/download/{file_id}",
            params={"conversation_id": conversation_id, "inline": "false"},
        )

    def download_file(self, url: str) -> bytes:
        """Download file content from a signed URL."""
        try:
            resp = self._session.get(
                url,
                headers={"User-Agent": USER_AGENT},
                cookies=self._cookies(),
            )
        except Exception as exc:
            raise NetworkError(f"Download failed: {exc}") from exc
        if resp.status_code != 200:
            raise ServerError(f"Download failed: {resp.status_code}", status_code=resp.status_code)
        return resp.content

    def _load_browser_cookies(self) -> list[dict]:
        """Load ChatGPT cookies from captured auth state for browser injection."""
        import json as _json

        project_root = Path(__file__).resolve().parents[4]
        for name in ("fresh-auth.json", "chatgpt-auth.json"):
            path = project_root / "traffic-capture" / name
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    state = _json.load(f)
                result = []
                for c in state.get("cookies", []):
                    if "chatgpt.com" not in c.get("domain", ""):
                        continue
                    cookie: dict = {
                        "name": c["name"], "value": c["value"],
                        "domain": c["domain"], "path": c.get("path", "/"),
                    }
                    if c.get("expires", -1) > 0:
                        cookie["expires"] = c["expires"]
                    if c.get("httpOnly"):
                        cookie["httpOnly"] = True
                    if c.get("secure"):
                        cookie["secure"] = True
                    result.append(cookie)
                return result
        return []

    def send_message(
        self,
        message: str,
        conversation_id: str | None = None,
        model: str | None = None,
        image_mode: bool = False,
    ) -> dict:
        """Send a message via Camoufox headless browser.

        Uses Camoufox (stealth Firefox) to bypass Cloudflare in headless mode.
        Returns dict with response text, conversation_id, file_id (for images).
        """
        if sys.platform == "win32":
            import asyncio
            asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

        try:
            from camoufox.sync_api import Camoufox
        except ImportError:
            raise NetworkError(
                "camoufox required for chat. Run: pip install camoufox && python -m camoufox fetch"
            )

        cookies = self._load_browser_cookies()

        with Camoufox(headless=True, humanize=True) as browser:
            page = browser.new_page()
            if cookies:
                browser.contexts[0].add_cookies(cookies)

            target_url = f"{BASE_URL}/c/{conversation_id}" if conversation_id else BASE_URL
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            textbox = page.get_by_role("textbox", name="Chat with ChatGPT")
            textbox.wait_for(state="visible", timeout=30000)

            # Select model if specified
            if model:
                try:
                    page.get_by_role("button", name="Model selector").click()
                    page.wait_for_timeout(1000)
                    selector = page.locator(f'[data-testid="model-switcher-{model}"]')
                    if selector.is_visible():
                        selector.click()
                        page.wait_for_timeout(500)
                    else:
                        # Close menu if model not found
                        page.keyboard.press("Escape")
                except Exception:
                    pass

            actual_message = f"Generate an image: {message}" if image_mode else message

            textbox.click()
            textbox.fill(actual_message)
            page.wait_for_timeout(300)

            send_btn = page.get_by_role("button", name="Send prompt")
            send_btn.click()

            # Wait for response completion by polling
            timeout_ms = 120000 if image_mode else 60000
            max_polls = timeout_ms // 2000
            for _ in range(max_polls):
                page.wait_for_timeout(2000)
                done = page.evaluate("""() => {
                    // Image done: download button present
                    if (document.querySelector('button[aria-label*="Download this image"]')) return true;
                    // Text done: copy response button present
                    if (document.querySelectorAll('button[aria-label="Copy response"]').length > 0) return true;
                    // Also check: assistant message has content
                    const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
                    if (msgs.length > 0) {
                        const last = msgs[msgs.length - 1];
                        if ((last.textContent?.trim().length || 0) > 5) return true;
                    }
                    return false;
                }""")
                if done:
                    page.wait_for_timeout(1500)
                    break

            # Extract response
            result = page.evaluate(r"""() => {
                const urlMatch = window.location.pathname.match(/\/c\/([a-f0-9-]+)/);
                const conv_id = urlMatch ? urlMatch[1] : null;

                // Text: find last non-empty assistant message
                let text = '';
                const msgs = document.querySelectorAll('[data-message-author-role="assistant"]');
                for (let i = msgs.length - 1; i >= 0; i--) {
                    const msg = msgs[i];
                    const md = msg.querySelector('.markdown');
                    if (md) {
                        const t = md.innerText?.trim() || '';
                        // Check if it's a clean markdown response (not canvas widget)
                        if (t && !t.startsWith('ChatGPT Instruments')) {
                            text = t;
                            break;
                        }
                        // Canvas/instruments widget: the answer is in an input element
                        const input = msg.querySelector('input, textarea');
                        if (input && input.value) {
                            text = input.value;
                            break;
                        }
                        // Fallback: extract from textContent, strip UI noise
                        const raw = msg.textContent || '';
                        const cleaned = raw
                            .replace(/ChatGPT Instruments/g, '')
                            .replace(/Give feedback/g, '')
                            .replace(/Copy response/g, '')
                            .trim();
                        if (cleaned) {
                            text = cleaned;
                            break;
                        }
                    } else if (msg.innerText?.trim()) {
                        text = msg.innerText.trim();
                        break;
                    }
                }

                // Image file_id
                let file_id = null;
                const genImgs = document.querySelectorAll('img[alt*="Generated image"]');
                if (genImgs.length > 0) {
                    const m = genImgs[genImgs.length - 1].src?.match(/file_[0-9a-f]+/);
                    if (m) file_id = m[0];
                }
                if (!file_id) {
                    for (const img of document.querySelectorAll('img[src*="file_"]')) {
                        if (img.src.includes('estuary/content')) {
                            const m = img.src.match(/file_[0-9a-f]+/);
                            if (m) { file_id = m[0]; break; }
                        }
                    }
                }

                return {text, file_id, conversation_id: conv_id};
            }""")

            # Get download URL for images
            if image_mode and result.get("file_id") and result.get("conversation_id"):
                try:
                    dl_info = self.get_file_download_url(
                        result["file_id"], result["conversation_id"]
                    )
                    result["download_url"] = dl_info.get("download_url")
                except Exception:
                    result["download_url"] = None

            return result
