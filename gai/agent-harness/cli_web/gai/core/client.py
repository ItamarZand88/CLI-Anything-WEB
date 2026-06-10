"""Playwright-based browser client for Google AI Mode."""

import sys
import urllib.parse

from playwright.sync_api import Page, sync_playwright

from .exceptions import BrowserError, CaptchaError, NetworkError, ParseError, TimeoutError
from .models import SearchResult, Source

# Windows event loop fix for Playwright
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

_SEARCH_URL = "https://www.google.com/search"
_DEFAULT_TIMEOUT = 30000
_ANSWER_SELECTOR = ".Y3BBE"
_TURN_SELECTOR = "[data-subtree=aimc]"
_COMPLETE_SELECTOR = "[data-complete=true]"


class GAIClient:
    """Headless browser client for Google AI Mode queries."""

    def __init__(self, headless: bool = True, lang: str = "en", timeout: int = _DEFAULT_TIMEOUT):
        self._headless = headless
        self._lang = lang
        self._timeout = timeout
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def _ensure_browser(self) -> Page:
        """Launch browser if needed and return the active page."""
        if self._page and not self._page.is_closed():
            return self._page

        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=self._headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
            )

            self._context = self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                locale=self._lang,
                viewport={"width": 1280, "height": 720},
            )

            self._page = self._context.new_page()

            return self._page
        except Exception as e:
            raise BrowserError(f"Failed to launch browser: {e}") from e

    def search(self, query: str) -> SearchResult:
        """Submit a new query to Google AI Mode.

        Opens the AI Mode URL with the given query and waits for the
        AI-generated response to complete.
        """
        page = self._ensure_browser()

        params = urllib.parse.urlencode({"q": query, "udm": "50", "hl": self._lang})
        url = f"{_SEARCH_URL}?{params}"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self._timeout)
        except Exception as e:
            raise NetworkError(f"Failed to load Google AI Mode: {e}") from e

        return self._wait_and_extract(page, query)

    def followup(self, query: str) -> SearchResult:
        """Ask a follow-up question in the current conversation.

        Requires a previous search() call in this session.
        """
        page = self._ensure_browser()

        if _SEARCH_URL not in (page.url or ""):
            raise BrowserError("No active conversation. Run 'search' first.")

        turn_count_before = page.evaluate(
            "() => document.querySelectorAll('[data-subtree=aimc]').length"
        )

        try:
            page.wait_for_selector("textarea", timeout=5000)
            textarea = page.query_selector("textarea")
            if not textarea:
                raise ParseError("Follow-up input not found on page.")
            textarea.focus()
            textarea.fill(query)
            page.keyboard.press("Enter")
        except ParseError:
            raise
        except Exception as e:
            raise BrowserError(f"Failed to submit follow-up: {e}") from e

        try:
            page.wait_for_function(
                f"() => document.querySelectorAll('[data-subtree=aimc]').length > {turn_count_before}",
                timeout=self._timeout,
            )
        except Exception as exc:
            raise TimeoutError(
                f"Follow-up response did not appear within {self._timeout // 1000}s.",
                timeout_seconds=self._timeout / 1000,
            ) from exc

        return self._wait_and_extract(page, query)

    def _wait_and_extract(self, page: Page, query: str) -> SearchResult:
        """Wait for the AI response to complete and extract it."""
        # Check for CAPTCHA
        try:
            captcha = page.query_selector("#captcha-form, .g-recaptcha, #recaptcha")
            if captcha:
                raise CaptchaError(
                    "Google presented a CAPTCHA. Please solve it in a browser and try again."
                )
        except CaptchaError:
            raise

        # Wait for AI Mode turn to appear
        try:
            page.wait_for_selector(_TURN_SELECTOR, timeout=self._timeout)
        except Exception as exc:
            raise TimeoutError(
                f"AI Mode response did not appear within {self._timeout // 1000}s. "
                "Google may not have returned an AI response for this query.",
                timeout_seconds=self._timeout / 1000,
            ) from exc

        # Wait for response completion marker
        try:
            page.wait_for_function(
                """() => {
                    const turns = document.querySelectorAll('[data-subtree=aimc]');
                    const last = turns[turns.length - 1];
                    return last && last.querySelector('[data-complete=true]');
                }""",
                timeout=self._timeout,
            )
        except Exception:
            pass  # proceed anyway

        # Wait for source links to appear
        try:
            page.wait_for_function(
                """() => {
                    const turns = document.querySelectorAll('[data-subtree=aimc]');
                    const last = turns[turns.length - 1];
                    return last && last.querySelector('a[data-ved]');
                }""",
                timeout=5000,
            )
        except Exception:
            pass  # proceed anyway

        # Small delay to let final rendering settle
        page.wait_for_timeout(500)

        return self._extract_result(page, query)

    def _extract_result(self, page: Page, query: str) -> SearchResult:
        """Extract the AI-generated answer and sources from the page."""
        result = page.evaluate(
            """() => {
            const turns = document.querySelectorAll('[data-subtree=aimc]');
            const lastTurn = turns[turns.length - 1];
            if (!lastTurn) return null;

            // Extract answer text from .Y3BBE sections
            const sections = lastTurn.querySelectorAll('.Y3BBE');
            const parts = [];
            for (const sec of sections) {
                // Clone to remove inline source buttons before extracting text
                const clone = sec.cloneNode(true);
                // Remove ALL buttons (source citations like "Teradata +2", "Show links")
                const buttons = clone.querySelectorAll('[role=button], button, [jsaction]');
                for (const b of buttons) {
                    const text = (b.innerText || '').trim();
                    // Remove citation buttons: "SiteName +N" or just "+N"
                    if (text.match(/\\+\\d+$/) || text.match(/^\\d+ sites?$/i)) {
                        b.remove();
                    }
                }
                const text = clone.innerText.trim();
                if (text) parts.push(text);
            }

            // Extract source links \u2014 handle Google redirect URLs and empty-text links
            const sources = [];
            const seen = new Set();
            const links = lastTurn.querySelectorAll('a[href][data-ved]');
            for (const a of links) {
                let href = a.href;
                if (!href) continue;

                // Resolve Google redirect URLs: /url?q=https://example.com/...
                try {
                    const u = new URL(href);
                    if (u.hostname.includes('google.com') && u.pathname === '/url') {
                        const target = u.searchParams.get('q') || u.searchParams.get('url');
                        if (target) href = target;
                    }
                } catch(e) {}

                // Skip Google internal links
                if (href.includes('google.com') || href.includes('gstatic.com')) continue;
                if (!href.startsWith('http')) continue;

                // Strip URL fragment (#:~:text=...)
                const cleanHref = href.split('#')[0];
                if (seen.has(cleanHref)) continue;
                seen.add(cleanHref);

                // Get title: first try link text, then parent container text
                let title = a.innerText.trim().split('\\n')[0];
                if (!title || title.length < 4) {
                    // Links may have empty text \u2014 extract domain as fallback title
                    try {
                        const domain = new URL(cleanHref).hostname.replace('www.', '');
                        title = domain;
                    } catch(e) { title = cleanHref.substring(0, 60); }
                }

                // Skip citation numbers
                if (title.match(/^\\+?\\d+$/)) continue;

                // Look for snippet near the link in parent container
                let snippet = '';
                const card = a.closest('li, [class]');
                if (card) {
                    const allText = card.innerText.trim();
                    const lines = allText.split('\\n').filter(l => l.length > 30);
                    for (const line of lines) {
                        if (line !== title && line.length > 30) {
                            snippet = line.substring(0, 200);
                            break;
                        }
                    }
                }

                sources.push({title: title.substring(0, 200), url: cleanHref, snippet: snippet});
            }

            // Check for follow-up prompt (last section often suggests next questions)
            let followUp = '';
            if (parts.length > 0) {
                const last = parts[parts.length - 1];
                if (last.includes('?') && last.length < 200) {
                    followUp = last;
                    parts.pop();
                }
            }

            return {
                answer: parts.join('\\n\\n'),
                sources: sources.slice(0, 20),
                followUp: followUp
            };
        }"""
        )

        if not result:
            raise ParseError("Could not extract AI response from page.")

        sources = [
            Source(
                title=s.get("title", ""),
                url=s.get("url", ""),
                snippet=s.get("snippet", ""),
            )
            for s in result.get("sources", [])
        ]

        return SearchResult(
            query=query,
            answer=result.get("answer", ""),
            sources=sources,
            follow_up_prompt=result.get("followUp", ""),
        )

    def close(self):
        """Close all browser resources."""
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._pw = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
