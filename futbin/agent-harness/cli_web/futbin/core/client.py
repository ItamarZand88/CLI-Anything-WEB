"""HTTP client for FUTBIN — handles requests, HTML parsing, rate limiting."""
from __future__ import annotations

import time
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from cli_web.futbin.core.models import Player, SBC, Evolution, MarketItem

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

    def _get(self, path: str, params: Optional[dict] = None) -> httpx.Response:
        """Rate-limited GET request."""
        elapsed = time.time() - self._last_request
        if elapsed < REQUEST_DELAY:
            time.sleep(REQUEST_DELAY - elapsed)
        resp = self._client.get(path, params=params)
        self._last_request = time.time()
        resp.raise_for_status()
        return resp

    def _soup(self, path: str, params: Optional[dict] = None) -> BeautifulSoup:
        resp = self._get(path, params)
        return BeautifulSoup(resp.text, "html.parser")

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
        """Fetch full player detail including stats and prices."""
        # First search to get the slug
        results = self.search_players(str(player_id), year=year)
        if not results:
            return None
        player = results[0]
        if player.id != player_id:
            # Try direct URL
            slug = str(player_id)
        else:
            slug = player.url.split("/")[-1] if player.url else str(player_id)

        url = f"/{year}/player/{player_id}/{slug}"
        soup = self._soup(url)
        return self._parse_player_detail(soup, player_id, year, player.url)

    def _parse_player_detail(
        self, soup: BeautifulSoup, player_id: int, year: int, url: str
    ) -> Player:
        """Parse player detail page."""
        # Name from title
        title = soup.find("title")
        name = ""
        if title:
            # "Kylian Mbappé EA FC 26 - 91 - Rating and Price | FUTBIN"
            name = title.text.split(" EA FC")[0].strip()

        # Rating from page
        rating = 0
        rating_el = soup.find(class_=re.compile(r"rating|player-rating"))
        if rating_el:
            try:
                rating = int(rating_el.get_text(strip=True))
            except ValueError:
                pass

        # Stats
        stats = {}
        for stat_name in ("pac", "sho", "pas", "dri", "def", "phy"):
            el = soup.find(attrs={"data-stat": stat_name}) or soup.find(
                class_=re.compile(rf"\b{stat_name}\b", re.IGNORECASE)
            )
            if el:
                try:
                    stats[stat_name] = int(el.get_text(strip=True))
                except ValueError:
                    pass

        # Prices — look for ps/xbox price spans
        ps_price = None
        xbox_price = None
        for el in soup.find_all(attrs={"data-platform": True}):
            platform = el.get("data-platform", "").lower()
            price_text = el.get_text(strip=True).replace(",", "").replace(".", "")
            val = _coin_str_to_int(price_text)
            if "ps" in platform:
                ps_price = val
            elif "xbox" in platform or "xb" in platform:
                xbox_price = val

        # Club/nation from meta or structured data
        club = ""
        nation = ""
        desc = soup.find("meta", attrs={"name": "description"})
        if desc:
            content = desc.get("content", "")
            # "Kylian Mbappé Gold Rare - EA FC 26 - 91 rating, prices..."
            pass  # not reliable for club/nation

        # Position
        position = ""
        pos_el = soup.find(class_=re.compile(r"player-position|position"))
        if pos_el:
            position = pos_el.get_text(strip=True)

        # Version from URL or page structure
        version = ""

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
    ) -> list[Player]:
        """List players from database with optional filters."""
        params: dict[str, Any] = {}
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
            params["overall"] = f"{lo}-{hi}"
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
        return self._parse_player_table(soup, year)

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

                # Prices — td.platform-ps-only / td.platform-pc-only
                # Price text is the first text node inside div.price, before the coin <img>
                ps_price = None
                xbox_price = None
                ps_cell = row.find("td", class_=lambda c: c and "platform-ps-only" in c)
                if ps_cell:
                    price_div = ps_cell.find(class_="price")
                    if price_div:
                        price_text = price_div.find(string=True, recursive=False)
                        if price_text:
                            ps_price = _coin_str_to_int(str(price_text).strip())
                pc_cell = row.find("td", class_=lambda c: c and "platform-pc-only" in c)
                if pc_cell:
                    price_div = pc_cell.find(class_="price")
                    if price_div:
                        price_text = price_div.find(string=True, recursive=False)
                        if price_text:
                            xbox_price = _coin_str_to_int(str(price_text).strip())

                players.append(
                    Player(
                        id=pid,
                        name=name,
                        position=position,
                        version="",
                        rating=rating,
                        club="",
                        nation="",
                        year=year,
                        url=href,
                        ps_price=ps_price,
                        xbox_price=xbox_price,
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

    def get_sbc(self, sbc_id: int, year: int = DEFAULT_YEAR) -> Optional[dict]:
        """Get SBC detail page."""
        soup = self._soup(f"/{year}/squad-building-challenge/{sbc_id}")
        title_el = soup.find("h1") or soup.find("title")
        name = title_el.get_text(strip=True) if title_el else f"SBC {sbc_id}"
        text = soup.get_text(" ", strip=True)
        return {
            "id": sbc_id,
            "name": name,
            "year": year,
            "url": f"{BASE_URL}/{year}/squad-building-challenge/{sbc_id}",
            "raw_text": text[:2000],
        }

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

    def get_evolution(self, evo_id: int) -> Optional[dict]:
        """Get evolution detail page."""
        soup = self._soup(f"/evolutions/{evo_id}")
        title_el = soup.find("h1") or soup.find("title")
        name = title_el.get_text(strip=True) if title_el else f"Evolution {evo_id}"
        text = soup.get_text(" ", strip=True)
        return {
            "id": evo_id,
            "name": name,
            "url": f"{BASE_URL}/evolutions/{evo_id}",
            "raw_text": text[:3000],
        }

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
