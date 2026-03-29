"""HTTP client for FUTBIN — handles requests, HTML parsing, rate limiting."""
from __future__ import annotations

import time
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from cli_web.futbin.core.models import Player, SBC, Evolution, MarketItem, MarketDetail, PriceHistory, FodderTier
from .exceptions import (
    FutbinError, NetworkError, RateLimitError, ServerError,
    NotFoundError, ParsingError, InvalidInputError,
)

BASE_URL = "https://www.futbin.com"
DEFAULT_YEAR = 26
REQUEST_DELAY = 0.5  # seconds between requests — be respectful


def _coin_str_to_int(value: str) -> Optional[int]:
    """Convert '1.2M', '150K', '1,234' to int."""
    if not value:
        return None
    value = value.strip().replace(",", "")
    try:
        if value.upper().endswith("M"):
            return int(float(value[:-1]) * 1_000_000)
        if value.upper().endswith("K"):
            return int(float(value[:-1]) * 1_000)
        return int(float(value))
    except (ValueError, AttributeError):
        return None


class FutbinClient:
    def __init__(self):
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": BASE_URL,
            },
            follow_redirects=True,
            timeout=30.0,
        )
        self._last_request = 0.0

    BASE_URL = BASE_URL

    def _get(self, path: str, params: Optional[dict] = None) -> httpx.Response:
        """Rate-limited GET request."""
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        try:
            resp = self._client.get(path, params=params)
        except httpx.ConnectError as exc:
            raise NetworkError(f"Connection failed: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Request error: {exc}") from exc
        self._last_request = time.time()
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise RateLimitError(
                "Rate limited by FUTBIN",
                retry_after=float(retry_after) if retry_after else None,
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Not found: {path}")
        if resp.status_code >= 500:
            raise ServerError(f"Server error {resp.status_code}: {path}", status_code=resp.status_code)
        resp.raise_for_status()
        return resp

    def _soup(self, path: str, params: Optional[dict] = None) -> BeautifulSoup:
        resp = self._get(path, params)
        soup = BeautifulSoup(resp.text, "html.parser")
        if not soup.body and not soup.find():
            raise ParsingError(f"Empty or unparseable response from {path}")
        return soup

    # ──────────────────────────────────────────────
    # Player Search (JSON API)
    # ──────────────────────────────────────────────

    def search_players(
        self, query: str, year: int = DEFAULT_YEAR, evolutions: bool = False
    ) -> list[Player]:
        resp = self._get(
            "/players/search",
            params={
                "targetPage": "PLAYER_PAGE",
                "query": query,
                "year": str(year),
                "evolutions": "true" if evolutions else "false",
            },
        )
        data = resp.json()
        players = []
        for item in data:
            rating_sq = item.get("ratingSquare", {})
            club = (
                item.get("clubImage", {})
                .get("fixed", {})
                .get("name", "")
            )
            nation = (
                item.get("nationImage", {})
                .get("fixed", {})
                .get("name", "")
            )
            url = item.get("location", {}).get("url", "")
            players.append(
                Player(
                    id=item["id"],
                    name=item.get("name", ""),
                    position=item.get("position", ""),
                    version=item.get("version", ""),
                    rating=int(rating_sq.get("rating", 0)),
                    club=club,
                    nation=nation,
                    year=year,
                    url=url,
                )
            )
        return players

    # ──────────────────────────────────────────────
    # Player Detail (HTML scraping)
    # ──────────────────────────────────────────────

    def get_player(self, player_id: int, year: int = DEFAULT_YEAR) -> Optional[Player]:
        """Fetch full player detail including stats and prices.

        FUTBIN requires the slug in the URL (/{year}/player/{id}/{slug}).
        We search first to find the slug, then scrape the detail page.
        If search doesn't find the exact ID, we try a common slug pattern.
        """
        # Search to find the player and get the canonical slug URL
        results = self.search_players(str(player_id), year=year)
        player = next((p for p in results if p.id == player_id), None)

        if player and player.url:
            # Got slug from search — use it
            path = player.url if player.url.startswith("/") else f"/{player.url}"
            soup = self._soup(path)
            return self._parse_player_detail(soup, player_id, year, player.url)

        # Search didn't find exact ID — try direct URL with placeholder slug
        # FUTBIN sometimes works with any slug if the ID is valid
        try:
            soup = self._soup(f"/{year}/player/{player_id}/player")
            return self._parse_player_detail(soup, player_id, year,
                                             f"/{year}/player/{player_id}")
        except (NotFoundError, ParsingError):
            return None

    def _parse_player_detail(
        self, soup: BeautifulSoup, player_id: int, year: int, url: str
    ) -> Player:
        """Parse player detail page.

        The page contains multiple player cards (different versions).
        The FIRST card is the one matching the URL. We also extract
        the price from the first .price-box-original-player element.
        """
        # Name from title: "Kylian Mbappé EA FC 26 - 91 - Rating and Price | FUTBIN"
        name = ""
        title = soup.find("title")
        if title:
            name = title.text.split(" EA FC")[0].strip()

        # Rating — first playercard rating element on page (matches the URL's card)
        rating = 0
        rating_el = soup.find(class_=re.compile(r"playercard-\d+-rating$"))
        if rating_el:
            try:
                rating = int(rating_el.get_text(strip=True))
            except ValueError:
                pass

        # Position — first playercard position element
        position = ""
        pos_el = soup.find(class_=re.compile(r"playercard-\d+-position$"))
        if pos_el:
            position = pos_el.get_text(strip=True)

        # Stats — from the first set of playercard stat-number elements
        stats = {}
        stat_pairs = soup.find_all(class_="playercard-stats")
        stat_names = ["pac", "sho", "pas", "dri", "def", "phy"]
        for i, stat_name in enumerate(stat_names):
            if i < len(stat_pairs):
                num_el = stat_pairs[i].find(class_="playercard-stat-number")
                if num_el:
                    try:
                        stats[stat_name] = int(num_el.get_text(strip=True))
                    except ValueError:
                        pass

        # Prices — from the first .price-box-original-player for each platform
        ps_price = None
        xbox_price = None  # PC price
        ps_box = soup.find(class_=lambda c: c and "price-box-original-player" in c and "platform-ps-only" in c)
        if ps_box:
            price_el = ps_box.find(class_="lowest-price-1")
            if price_el:
                ps_price = _coin_str_to_int(price_el.get_text(strip=True))
        pc_box = soup.find(class_=lambda c: c and "price-box-original-player" in c and "platform-pc-only" in c)
        if pc_box:
            price_el = pc_box.find(class_="lowest-price-1")
            if price_el:
                xbox_price = _coin_str_to_int(price_el.get_text(strip=True))

        # Version — from meta description ("Gold Rare", "TOTY", etc.)
        version = ""
        desc_el = soup.find("meta", attrs={"name": "description"})
        if desc_el:
            content = desc_el.get("content", "")
            # "Kylian Mbappé Gold Rare - EA FC 26 ..."
            m = re.search(r"(?:Mbappé|" + re.escape(name.split()[-1] if name else "") + r")\s+(.+?)\s*-\s*EA FC", str(content))
            if m:
                version = m.group(1).strip()

        # Club/nation — not reliably available from the detail page HTML
        club = ""
        nation = ""

        return Player(
            id=player_id,
            name=name,
            position=position,
            version=version,
            rating=rating,
            club=club,
            nation=nation,
            year=year,
            url=url,
            ps_price=ps_price,
            xbox_price=xbox_price,
            stats=stats,
        )

    # ──────────────────────────────────────────────
    # Players List (HTML scraping)
    # ──────────────────────────────────────────────

    def list_players(
        self,
        name: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        sort: str = "ps_price",
        order: str = "desc",
        year: int = DEFAULT_YEAR,
        page: int = 1,
        position: Optional[str] = None,
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        version: Optional[str] = None,
        platform: str = "ps",
        min_skills: Optional[int] = None,
        min_wf: Optional[int] = None,
        gender: Optional[str] = None,
        league: Optional[int] = None,
        nation: Optional[int] = None,
        club: Optional[int] = None,
    ) -> tuple[list[Player], bool]:
        """List players from database with optional filters.

        Returns (players, has_next_page).
        """
        params: dict[str, Any] = {}
        if page > 1:
            params["page"] = str(page)
        if name:
            params["name"] = name
        if min_price is not None or max_price is not None:
            lo = min_price or 0
            hi = max_price or 10_000_000
            price_param = "pc_price" if platform == "pc" else "ps_price"
            params[price_param] = f"{lo}-{hi}"
        if sort:
            # Map user-friendly aliases to URL param values
            sort_map = {"rating": "overall"}
            params["sort"] = sort_map.get(sort, sort)
            params["order"] = order
        if position:
            params["position"] = position.upper()
        if rating_min is not None or rating_max is not None:
            lo = rating_min or 40
            hi = rating_max or 99
            params["player_rating"] = f"{lo}-{hi}"
        if version:
            params["version"] = version
        if min_skills is not None:
            params["min_skills"] = str(min_skills)
        if min_wf is not None:
            params["min_wf"] = str(min_wf)
        if gender:
            params["gender"] = gender
        if league is not None:
            params["league"] = str(league)
        if nation is not None:
            params["nation"] = str(nation)
        if club is not None:
            params["club"] = str(club)

        soup = self._soup("/players", params)
        players = self._parse_player_table(soup, year)
        # Check for pagination "next" link
        has_next_page = False
        next_link = soup.find("a", attrs={"rel": "next"})
        if not next_link:
            # Also check for next page item in pagination
            page_items = soup.find_all("li", class_="page-item")
            for item in page_items:
                link = item.find("a")
                if link and ("next" in link.get("rel", []) or "next" in link.get("aria-label", "").lower() or "»" in link.get_text()):
                    has_next_page = True
                    break
        else:
            has_next_page = True
        return (players, has_next_page)

    def _parse_player_table(self, soup: BeautifulSoup, year: int) -> list[Player]:
        """Parse the players table from /players page."""
        players = []
        table = soup.find("table", id=re.compile(r"player|players", re.IGNORECASE))
        if not table:
            table = soup.find("table")
        if not table:
            return players

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue
            try:
                # Player URL — from the playercard link (has /26/player/<id>/<slug>)
                link = row.find("a", href=re.compile(r"/\d+/player/"))
                if not link:
                    continue
                href = link.get("href", "")
                parts = href.strip("/").split("/")
                # /26/player/40/kylian-mbappe -> ['26','player','40','kylian-mbappe']
                if len(parts) < 3:
                    continue
                pid = int(parts[2]) if parts[1] == "player" else int(parts[-2])

                # Name — use the dedicated name link, NOT the playercard link
                # (playercard link text returns the rating number from the mini card)
                name_link = row.find("a", class_="table-player-name")
                if name_link:
                    name = name_link.get_text(strip=True)
                else:
                    name = parts[-1].replace("-", " ").title()

                # Rating — td.table-rating contains only the number
                rating = 0
                rating_cell = row.find("td", class_=re.compile(r"table-rating"))
                if rating_cell:
                    try:
                        rating = int(rating_cell.get_text(strip=True))
                    except ValueError:
                        pass

                # Position — first <span> inside div.table-pos-main (drops "++" suffix span)
                position = ""
                pos_cell = row.find("td", class_=re.compile(r"table-pos"))
                if pos_cell:
                    pos_main = pos_cell.find(class_="table-pos-main")
                    if pos_main:
                        first_span = pos_main.find("span")
                        if first_span:
                            position = first_span.get_text(strip=True)
                    if not position:
                        position = pos_cell.get_text(strip=True)

                # Version — card type from td[0] (e.g., "TOTY", "Icons", "FUT Birthday")
                # The version text appears after the player name in the name cell
                version = ""
                name_cell = row.find("td", class_="table-name")
                if name_cell:
                    # Look for card type badges/labels
                    version_el = name_cell.find(class_=re.compile(r"card-type|version|label"))
                    if version_el:
                        version = version_el.get_text(strip=True)
                    if not version:
                        # Fallback: extract version from the full cell text after the name
                        full_text = name_cell.get_text(" ", strip=True)
                        # Remove rating number and name to get version
                        for suffix in [name, str(rating)]:
                            full_text = full_text.replace(suffix, "")
                        leftover = full_text.strip()
                        if leftover and leftover not in ("", name):
                            version = leftover.strip()

                # Club & Nation — from img title attributes in name cell
                club = ""
                nation = ""
                if name_cell:
                    for img in name_cell.find_all("img"):
                        alt = img.get("alt", "")
                        title = img.get("title", "")
                        if alt == "Club" and title and not club:
                            club = title
                        elif alt == "Nation" and title and not nation:
                            nation = title

                # Stats — from dedicated table columns (PAC/SHO/PAS/DRI/DEF/PHY)
                stats = {}
                stat_map = {
                    "table-pace": "pac",
                    "table-shooting": "sho",
                    "table-passing": "pas",
                    "table-dribbling": "dri",
                    "table-defending": "def",
                    "table-physicality": "phy",
                }
                for css_class, stat_key in stat_map.items():
                    stat_cell = row.find("td", class_=css_class)
                    if stat_cell:
                        try:
                            stats[stat_key] = int(stat_cell.get_text(strip=True))
                        except ValueError:
                            pass

                # Prices — td.platform-ps-only / td.platform-pc-only
                # or td.table-cross-price (used on /latest page)
                ps_price = None
                xbox_price = None
                ps_cell = row.find("td", class_=lambda c: c and ("platform-ps-only" in c or "table-cross-price" in c))
                if ps_cell:
                    price_text = ps_cell.get_text(strip=True)
                    # Price text may include % change suffix — take first part
                    price_part = re.split(r'[+-]?\d+\.\d+%', price_text)[0].strip()
                    if price_part:
                        ps_price = _coin_str_to_int(price_part)
                pc_cell = row.find("td", class_=lambda c: c and ("platform-pc-only" in c or "table-pc-price" in c))
                if pc_cell:
                    price_text = pc_cell.get_text(strip=True)
                    price_part = re.split(r'[+-]?\d+\.\d+%', price_text)[0].strip()
                    if price_part:
                        xbox_price = _coin_str_to_int(price_part)

                players.append(
                    Player(
                        id=pid,
                        name=name,
                        position=position,
                        version=version,
                        rating=rating,
                        club=club,
                        nation=nation,
                        year=year,
                        url=href,
                        ps_price=ps_price,
                        xbox_price=xbox_price,
                        stats=stats,
                    )
                )
            except (ValueError, IndexError):
                continue
        return players

    # ──────────────────────────────────────────────
    # Market Index
    # ──────────────────────────────────────────────

    def get_market_index(self) -> list[MarketItem]:
        """Fetch market index data."""
        soup = self._soup("/market/index-table")
        items = []
        rows = soup.find_all("tr")
        for row in rows[1:]:  # skip header
            cells = row.find_all("td")
            if len(cells) >= 3:
                name_el = cells[0].find("a") or cells[0]
                items.append(
                    MarketItem(
                        name=name_el.get_text(strip=True),
                        last=cells[1].get_text(strip=True),
                        change_pct=cells[2].get_text(strip=True),
                    )
                )
        return items

    def get_market_detail(self, rating: str) -> MarketDetail:
        """Fetch detailed market index for a rating tier (e.g. '83', '100', 'icons').

        Returns current value plus open/lowest/highest from /market/{rating}.
        """
        # Normalize: "icons" -> "Icons", "100" -> base /market
        rating_path = rating
        if rating.lower() == "icons":
            rating_path = "Icons"
        path = "/market" if rating in ("100", "index") else f"/market/{rating_path}"
        soup = self._soup(path)
        html = str(soup)

        # Current value + change %
        current = ""
        change_pct = ""
        # The index table on the page has the current values too
        items = []
        rows = soup.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) >= 3:
                name_el = cells[0].find("a") or cells[0]
                row_name = name_el.get_text(strip=True)
                if rating in row_name.lower() or (rating == "100" and "100" in row_name):
                    current = cells[1].get_text(strip=True)
                    change_pct = cells[2].get_text(strip=True)
                    break

        # Open / Lowest / Highest from page text
        open_value = ""
        lowest = ""
        highest = ""
        m = re.search(r"Open:\s*([\d.]+)", html)
        if m:
            open_value = m.group(1)
        m = re.search(r"Lowest:\s*([\d.]+)", html)
        if m:
            lowest = m.group(1)
        m = re.search(r"Highest:\s*([\d.]+)", html)
        if m:
            highest = m.group(1)

        # Name for display
        name = f"Index {rating.upper()}" if not rating.isdigit() else f"Index {rating}"

        return MarketDetail(
            name=name, rating=rating, current=current,
            change_pct=change_pct, open_value=open_value,
            lowest=lowest, highest=highest,
        )

    # ──────────────────────────────────────────────
    # Popular Players
    # ──────────────────────────────────────────────

    def get_popular_players(self, limit: int = 50) -> list[Player]:
        """Fetch trending/popular players from /popular page."""
        soup = self._soup("/popular")
        return self._parse_playercard_grid(soup, limit=limit)

    # ──────────────────────────────────────────────
    # Latest Players
    # ──────────────────────────────────────────────

    def get_latest_players(self, page: int = 1) -> tuple[list[Player], bool]:
        """Fetch newly added players from /latest page. Returns (players, has_next)."""
        params = {}
        if page > 1:
            params["page"] = str(page)
        soup = self._soup("/latest", params)
        players = self._parse_player_table(soup, DEFAULT_YEAR)
        has_next = False
        next_link = soup.find("a", attrs={"rel": "next"})
        if not next_link:
            for item in soup.find_all("li", class_="page-item"):
                link = item.find("a")
                if link and ("next" in link.get("rel", []) or "next" in link.get("aria-label", "").lower() or "»" in link.get_text()):
                    has_next = True
                    break
        else:
            has_next = True
        return (players, has_next)

    # ──────────────────────────────────────────────
    # Price History
    # ──────────────────────────────────────────────

    def get_price_history(self, player_id: int, year: int = DEFAULT_YEAR) -> PriceHistory:
        """Fetch price history from player detail page data attributes."""
        # Search to find the player slug URL
        results = self.search_players(str(player_id), year=year)
        player = next((p for p in results if p.id == player_id), None)

        if player and player.url:
            path = player.url if player.url.startswith("/") else f"/{player.url}"
        else:
            path = f"/{year}/player/{player_id}/player"

        soup = self._soup(path)

        ps_data = []
        pc_data = []

        # Extract from data-ps-data / data-pc-data attributes on graph elements
        ps_el = soup.find(attrs={"data-ps-data": True})
        if ps_el:
            try:
                import json as _json
                ps_data = _json.loads(ps_el["data-ps-data"])
            except (ValueError, KeyError):
                pass

        pc_el = soup.find(attrs={"data-pc-data": True})
        if pc_el:
            try:
                import json as _json
                pc_data = _json.loads(pc_el["data-pc-data"])
            except (ValueError, KeyError):
                pass

        # Get player name from title
        name = ""
        title_el = soup.find("title")
        if title_el:
            name = title_el.text.split(" EA FC")[0].strip()

        return PriceHistory(
            player_id=player_id,
            player_name=name,
            year=year,
            ps_prices=ps_data,
            pc_prices=pc_data,
        )

    # ──────────────────────────────────────────────
    # SBC Fodder (cheapest by rating)
    # ──────────────────────────────────────────────

    def get_sbc_fodder(self) -> list["FodderTier"]:
        """Fetch cheapest players per rating tier from /squad-building-challenges/cheapest."""
        from .models import FodderPlayer
        soup = self._soup("/squad-building-challenges/cheapest")
        tiers = []
        seen_ratings = set()

        columns = soup.find_all(class_="stc-player-column")
        for col in columns:
            col_classes = col.get("class", [])
            if "hide-not-pc" not in col_classes:
                continue

            rating_el = col.find(class_="stc-rating")
            if not rating_el:
                continue
            try:
                rating = int(rating_el.get_text(strip=True))
            except ValueError:
                continue
            if rating in seen_ratings:
                continue
            seen_ratings.add(rating)

            players = []
            links = col.find_all("a", href=re.compile(r"/player/"))
            for link in links:
                href = link.get("href", "")
                parts = href.strip("/").split("/")
                if len(parts) < 3:
                    continue
                try:
                    pid = int(parts[2])
                except ValueError:
                    continue
                text = link.get_text(" ", strip=True)
                m = re.match(r"(.+?)\s*\((\w+)\)\s*([\d,.]+[KkMm]?)", text)
                if m:
                    players.append(FodderPlayer(
                        id=pid, name=m.group(1).strip(),
                        position=m.group(2), price=m.group(3),
                    ))

            if players:
                tiers.append(FodderTier(rating=rating, players=players))

        tiers.sort(key=lambda t: t.rating)
        return tiers

    # ──────────────────────────────────────────────
    # Market Movers (risers / fallers)
    # ──────────────────────────────────────────────

    def get_market_movers(
        self, direction: str = "risers", platform: str = "ps",
        page: int = 1, rating_min: int = 80,
        min_price: int = 1000, max_price: int = 15_000_000,
    ) -> tuple[list[Player], bool]:
        """Fetch biggest price movers. direction='risers' or 'fallers'."""
        price_field = f"{platform}_price" if platform == "ps" else "pc_price"
        order = "desc" if direction == "risers" else "asc"
        params: dict[str, Any] = {
            "sort": f"{price_field}_change",
            "order": order,
            f"{price_field}": f"{min_price}-{max_price}",
            "player_rating": f"{rating_min}-99",
        }
        if page > 1:
            params["page"] = str(page)

        soup = self._soup("/players", params)
        players = self._parse_player_table(soup, DEFAULT_YEAR)
        has_next = False
        next_link = soup.find("a", attrs={"rel": "next"})
        if not next_link:
            for item in soup.find_all("li", class_="page-item"):
                link = item.find("a")
                if link and ("next" in link.get("rel", []) or "»" in link.get_text()):
                    has_next = True
                    break
        else:
            has_next = True
        return (players, has_next)

    # ──────────────────────────────────────────────
    # Playercard grid parser (used by /popular)
    # ──────────────────────────────────────────────

    def _parse_playercard_grid(self, soup: BeautifulSoup, limit: int = 50) -> list[Player]:
        """Parse playercard-wrapper links from grid pages (/popular, etc.)."""
        players = []
        cards = soup.find_all("a", class_="playercard-wrapper", limit=limit)
        for card in cards:
            href = card.get("href", "")
            parts = href.strip("/").split("/")
            if len(parts) < 3 or parts[1] != "player":
                continue
            try:
                pid = int(parts[2])
            except ValueError:
                continue

            rating = 0
            rating_el = card.find(class_=re.compile(r"playercard-\d+-rating$"))
            if rating_el:
                try:
                    rating = int(rating_el.get_text(strip=True))
                except ValueError:
                    pass

            position = ""
            pos_el = card.find(class_=re.compile(r"playercard-\d+-position"))
            if pos_el:
                position = pos_el.get_text(strip=True)

            # Get name from URL slug (full name) since card only shows last name
            name = parts[-1].replace("-", " ").title() if len(parts) > 3 else ""
            if not name:
                # Fallback: try card name element
                name_el = card.find(class_="text-ellipsis")
                if name_el:
                    name = name_el.get_text(strip=True)
            if not name:
                name = f"Player {pid}"

            ps_price = None
            ps_el = card.find(class_="platform-ps-only")
            if ps_el:
                ps_price = _coin_str_to_int(ps_el.get_text(strip=True))

            pc_price = None
            pc_el = card.find(class_="platform-pc-only")
            if pc_el:
                pc_price = _coin_str_to_int(pc_el.get_text(strip=True))

            # Stats from card (PAC/SHO/PAS/DRI/DEF/PHY)
            stats = {}
            text = card.get_text(" ", strip=True)
            for stat_name in ("Pac", "Sho", "Pas", "Dri", "Def", "Phy"):
                m = re.search(rf"(\d+)\s*{stat_name}", text)
                if m:
                    stats[stat_name.lower()] = int(m.group(1))

            players.append(
                Player(
                    id=pid,
                    name=name,
                    position=position,
                    version="",
                    rating=rating,
                    club="",
                    nation="",
                    year=DEFAULT_YEAR,
                    url=href,
                    ps_price=ps_price,
                    xbox_price=pc_price,
                    stats=stats,
                )
            )
        return players

    # ──────────────────────────────────────────────
    # SBCs
    # ──────────────────────────────────────────────

    def list_sbcs(self, category: Optional[str] = None, year: int = DEFAULT_YEAR) -> list[SBC]:
        """List Squad Building Challenges."""
        params: dict = {}
        path = "/squad-building-challenges"
        if category:
            path = f"/squad-building-challenges/{category}"

        soup = self._soup(path, params)
        return self._parse_sbc_list(soup, year)

    def _parse_sbc_list(self, soup: BeautifulSoup, year: int) -> list[SBC]:
        sbcs = []
        # SBC cards use class "sbc-card-wrapper"
        cards = soup.find_all(class_="sbc-card-wrapper")
        for card in cards:
            link = card.find("a", href=re.compile(r"/squad-building-challenge/\d+"))
            if not link:
                continue
            href = link.get("href", "")
            parts = href.strip("/").split("/")
            try:
                sbc_id = int(parts[-1])
            except (ValueError, IndexError):
                continue

            # Name: first child div of "text-ellipsis" in card top area
            name = ""
            top_area = card.find(class_="og-card-wrapper-top")
            if top_area:
                name_container = top_area.find(class_="text-ellipsis")
                if name_container:
                    # Get the first direct child div (the SBC name, not the badge)
                    first_div = name_container.find("div")
                    if first_div:
                        name = first_div.get_text(strip=True)
                    else:
                        name = name_container.get_text(strip=True)
            if not name:
                name = f"SBC {sbc_id}"

            # Card full text for pattern extraction
            text = card.get_text(" ", strip=True)
            expires = ""
            cost_ps = None
            cost_xbox = None
            repeatable = "Repeatable" in text

            exp_m = re.search(r"Expires\s+(.+?)(?:\s+Repeatable|\s+Completed|\s*$)", text, re.IGNORECASE)
            if exp_m:
                expires = exp_m.group(1).strip()

            # Coin prices — look for patterns like "62.6K" near "Coin" or at end
            coin_matches = re.findall(r"([\d,]+(?:\.\d+)?[KkMm]?)\s*(?:Coin)?$|(?:^|\s)([\d,]+(?:\.\d+)?[KkMm])", text)
            # Look for the PS/Xbox prices at the end of the card text
            price_matches = re.findall(r"([\d]+(?:\.\d+)?[KkMm])", text)
            if price_matches:
                try:
                    cost_ps = _coin_str_to_int(price_matches[-2]) if len(price_matches) >= 2 else _coin_str_to_int(price_matches[-1])
                    cost_xbox = _coin_str_to_int(price_matches[-1]) if len(price_matches) >= 2 else None
                except (IndexError, ValueError):
                    pass

            # Reward
            reward = ""
            reward_el = card.find(class_=re.compile(r"reward"))
            if reward_el:
                reward = reward_el.get_text(strip=True)[:60]

            sbcs.append(
                SBC(
                    id=sbc_id,
                    name=name,
                    category="",
                    reward=reward,
                    expires=expires,
                    year=year,
                    cost_ps=cost_ps,
                    cost_xbox=cost_xbox,
                    repeatable=repeatable,
                )
            )
        return sbcs

    # ──────────────────────────────────────────────
    # Evolutions
    # ──────────────────────────────────────────────

    def list_evolutions(
        self,
        category: Optional[int] = None,
        expiring: bool = False,
        year: int = DEFAULT_YEAR,
    ) -> list[Evolution]:
        """List player evolutions."""
        params: dict = {"last_chance": "true" if expiring else "false"}
        if category is not None:
            params["category"] = str(category)

        soup = self._soup("/evolutions", params)
        return self._parse_evolution_list(soup, year)

    def _parse_evolution_list(self, soup: BeautifulSoup, year: int) -> list[Evolution]:
        evolutions = []
        # Evolution cards use class "evolutions-overview-wrapper"
        cards = soup.find_all(class_="evolutions-overview-wrapper")
        for card in cards:
            # Find the top link with the evolution ID
            top_link = card.find("a", class_="evolutions-card-top")
            if not top_link:
                continue
            href = top_link.get("href", "")
            parts = href.strip("/").split("/")
            try:
                evo_id = int(parts[1])
            except (ValueError, IndexError):
                continue

            # Name: text-center div inside the top link
            name = ""
            name_el = top_link.find(class_="text-center")
            if name_el:
                name = name_el.get_text(strip=True)
            if not name:
                name = parts[2].replace("-", " ").title() if len(parts) > 2 else f"Evo {evo_id}"

            # Category: first evolution-badge text
            category = ""
            badge = top_link.find(class_="evolution-badge")
            if badge:
                category = badge.get_text(strip=True)

            # Parse expiry and unlock from card text
            text = card.get_text(" ", strip=True)
            expires = ""
            unlock_time = ""
            repeatable = "Repeatable" in text

            exp_m = re.search(r"EXPIRES?\s+(.+?)(?:\s+UNLOCK|\s+Free|\s*$)", text, re.IGNORECASE)
            if exp_m:
                expires = exp_m.group(1).strip()
            unlock_m = re.search(r"UNLOCK\s+(.+?)(?:\s+EXPIRES|\s*$)", text, re.IGNORECASE)
            if unlock_m:
                unlock_time = unlock_m.group(1).strip()

            evolutions.append(
                Evolution(
                    id=evo_id,
                    name=name,
                    category=category,
                    expires=expires,
                    year=year,
                    unlock_time=unlock_time,
                    repeatable=repeatable,
                )
            )
        # Deduplicate by id
        seen = set()
        unique = []
        for e in evolutions:
            if e.id not in seen:
                seen.add(e.id)
                unique.append(e)
        return unique

    def compare_players(self, id1: int, id2: int, year: int = DEFAULT_YEAR) -> "PlayerComparison":
        """Compare two players side-by-side."""
        from .models import PlayerComparison
        p1 = self.get_player(id1, year=year)
        p2 = self.get_player(id2, year=year)
        if not p1:
            raise NotFoundError(f"Player {id1} not found")
        if not p2:
            raise NotFoundError(f"Player {id2} not found")

        diffs = {}
        stats1 = p1.stats or {}
        stats2 = p2.stats or {}
        all_stats = set(list(stats1.keys()) + list(stats2.keys()))
        for stat in sorted(all_stats):
            v1 = stats1.get(stat, 0)
            v2 = stats2.get(stat, 0)
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                diffs[stat] = {"player1": v1, "player2": v2, "diff": v1 - v2}

        return PlayerComparison(player1=p1, player2=p2, stat_diffs=diffs)

    def get_sbc_detail(self, sbc_id: int, year: int = DEFAULT_YEAR) -> "SBCDetail":
        """Get structured SBC details (requirements, rewards, description)."""
        from .models import SBCDetail
        url = f"/{year}/squad-building-challenge/{sbc_id}"
        soup = self._soup(url)
        if not soup:
            raise NotFoundError(f"SBC {sbc_id} not found")

        name = ""
        title_el = soup.find("h1") or soup.find(class_="sbc_name")
        if title_el:
            name = title_el.get_text(strip=True)

        # Extract description
        desc_el = soup.find(class_="sbc-desc") or soup.find(class_="sbc_desc")
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Extract requirements from requirement cards
        requirements = []
        req_sections = soup.find_all(class_=lambda c: c and ("requirement" in c.lower() if isinstance(c, str) else any("requirement" in x.lower() for x in c)))
        for section in req_sections[:10]:  # Limit to avoid noise
            text = section.get_text(" ", strip=True)
            if text and len(text) > 5:
                requirements.append({"text": text[:200]})

        # Extract reward
        reward = ""
        reward_el = soup.find(class_=lambda c: c and ("reward" in str(c).lower()))
        if reward_el:
            reward = reward_el.get_text(strip=True)[:200]

        return SBCDetail(
            id=sbc_id, name=name, year=year, description=description,
            requirements=requirements, reward=reward,
            url=f"{self.BASE_URL}{url}",
        )

    def get_evolution_detail(self, evo_id: int) -> "EvolutionDetail":
        """Get structured evolution details (requirements, upgrades)."""
        from .models import EvolutionDetail
        url = f"/evolutions/{evo_id}"
        soup = self._soup(url)
        if not soup:
            raise NotFoundError(f"Evolution {evo_id} not found")

        name = ""
        title_el = soup.find("h1")
        if title_el:
            name = title_el.get_text(strip=True)

        # Extract requirements
        requirements = []
        req_els = soup.find_all(class_=lambda c: c and ("req" in str(c).lower()))
        for el in req_els[:10]:
            text = el.get_text(" ", strip=True)
            if text and len(text) > 3:
                requirements.append({"text": text[:200]})

        # Extract upgrades/boosts
        upgrades = []
        upgrade_els = soup.find_all(class_=lambda c: c and ("upgrade" in str(c).lower() or "boost" in str(c).lower()))
        for el in upgrade_els[:10]:
            text = el.get_text(" ", strip=True)
            if text and len(text) > 3:
                upgrades.append({"text": text[:200]})

        return EvolutionDetail(
            id=evo_id, name=name, requirements=requirements,
            upgrades=upgrades, url=f"{self.BASE_URL}{url}",
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
