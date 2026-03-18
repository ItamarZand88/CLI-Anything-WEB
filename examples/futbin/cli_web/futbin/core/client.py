"""HTTP client for FUTBIN — handles both JSON API and HTML scraping."""

import json
import re
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .models import (
    Evolution,
    MarketIndex,
    Player,
    PlayerSearchResult,
    PriceHistory,
    PricePoint,
    SBC,
)

BASE_URL = "https://www.futbin.com"
DEFAULT_YEAR = "26"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL + "/",
}


def _parse_price(text: str) -> Optional[int]:
    """Parse price string like '2.73M', '690K', '3,600' into int."""
    text = text.strip().replace(",", "")
    if not text or text == "---":
        return None
    if text == "0":
        return 0
    text = text.upper()
    multiplier = 1
    if text.endswith("M"):
        multiplier = 1_000_000
        text = text[:-1]
    elif text.endswith("K"):
        multiplier = 1_000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return None


def _parse_int(text: str) -> Optional[int]:
    text = text.strip()
    try:
        return int(text)
    except ValueError:
        return None


def _parse_float(text: str) -> Optional[float]:
    text = text.strip()
    try:
        return float(text)
    except ValueError:
        return None


class FutbinClient:
    """HTTP client for futbin.com."""

    def __init__(self, cookies: Optional[dict] = None):
        self._cookies = cookies or {}
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers=DEFAULT_HEADERS,
            cookies=self._cookies,
            follow_redirects=True,
            timeout=30.0,
        )
        self._last_request_time = 0.0
        self._min_interval = 2.0  # seconds between requests (respect rate limits)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _rate_limit(self):
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _get(self, path: str, params: Optional[dict] = None) -> httpx.Response:
        """Make a GET request with rate limiting and error handling."""
        self._rate_limit()
        resp = self._client.get(path, params=params)
        if resp.status_code in (429, 403):
            # Rate limited or Cloudflare blocked — back off and retry
            retry_after = int(resp.headers.get("Retry-After", "10"))
            time.sleep(max(retry_after, 5))
            resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp

    def _get_soup(self, path: str, params: Optional[dict] = None) -> BeautifulSoup:
        """GET an HTML page and return parsed BeautifulSoup."""
        resp = self._get(path, params=params)
        return BeautifulSoup(resp.text, "html.parser")

    # ── Player Search (JSON API) ──────────────────────────────────────

    def search_players(self, query: str, year: str = DEFAULT_YEAR) -> list[PlayerSearchResult]:
        """Search players by name using the JSON API."""
        resp = self._get(
            "/players/search",
            params={
                "query": query,
                "year": year,
                "targetPage": "PLAYER_PAGE",
                "evolutions": "false",
            },
        )
        data = resp.json()
        results = []
        for item in data:
            results.append(PlayerSearchResult(
                id=item["id"],
                name=item["name"],
                position=item["position"],
                version=item.get("version", ""),
                rating=item.get("ratingSquare", {}).get("rating", ""),
                url=item.get("location", {}).get("url", ""),
            ))
        return results

    # ── Player List (HTML Scraping) ───────────────────────────────────

    def list_players(
        self,
        page: int = 1,
        position: Optional[str] = None,
        sort: str = "ps_price",
        order: str = "desc",
        version: Optional[str] = None,
        league: Optional[str] = None,
        nation: Optional[str] = None,
        club: Optional[str] = None,
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        accelerate: Optional[str] = None,
    ) -> list[Player]:
        """List players from the players page with filters.

        Server-side URL params:
        - position: GK,LB,CB,RB,CAM,CM,CDM,RM,LM,ST,RW,LW (comma-separated)
        - league: numeric ID (13=PL, 53=LaLiga, 31=SerieA, 19=Bundesliga, 16=Ligue1)
        - nation: numeric ID (52=Argentina, 14=Brazil, 18=France, etc.)
        - club: numeric ID
        - player_rating: MIN-MAX (e.g. 87-87)
        - ps_price: MIN-MAX or MIN+ (e.g. 200-400 or 200+)
        - accelerate: explosive|controlled|lengthy|c_explosive|c_controlled|c_lengthy
        - sort: ps_price|pc_price|Player_Rating|futbin_rating|name|popularity
        - order: asc|desc
        - page: number
        - p_squad: promo name (e.g. TOTY, FUTBirthday, TOTW26)
        """
        params = {"page": str(page), "sort": sort, "order": order}
        if position:
            params["position"] = position
        if version:
            params["p_squad"] = version
        if league:
            params["league"] = league
        if nation:
            params["nation"] = nation
        if club:
            params["club"] = club
        if accelerate:
            params["accelerate"] = accelerate
        # Server-side rating filter: player_rating=MIN-MAX
        if rating_min is not None or rating_max is not None:
            r_min = rating_min if rating_min is not None else 1
            r_max = rating_max if rating_max is not None else 99
            params["player_rating"] = f"{r_min}-{r_max}"
        # Server-side price filter: ps_price=MIN-MAX or ps_price=MIN+
        if price_min is not None or price_max is not None:
            if price_min is not None and price_max is not None:
                params["ps_price"] = f"{price_min}-{price_max}"
            elif price_min is not None:
                params["ps_price"] = f"{price_min}+"
            else:
                params["ps_price"] = f"0-{price_max}"

        soup = self._get_soup("/players", params=params)
        players = self._parse_player_table(soup)

        return players

    def _parse_player_table(self, soup: BeautifulSoup) -> list[Player]:
        """Parse the player table from HTML."""
        players = []
        # Find player rows — they are <tr> elements with player data
        rows = soup.select("table.futbin-table tbody tr, .player-table-row")
        if not rows:
            # Try alternative selectors
            rows = soup.select("tr[data-url]")

        for row in rows:
            player = self._parse_player_row(row)
            if player:
                players.append(player)
        return players

    def _parse_player_row(self, row) -> Optional[Player]:
        """Parse a single player row from the table.

        Table cells use CSS classes: table-name, table-rating, table-pos,
        table-price, table-foot, table-skills, table-weak-foot,
        table-pace, table-shooting, table-passing, table-dribbling,
        table-defending, table-physicality, table-popularity, table-in-game-stats
        """
        # Extract player link and ID
        link = row.select_one("a[href*='/player/']")
        if not link:
            return None

        href = link.get("href", "")
        id_match = re.search(r"/player/(\d+)", href)
        if not id_match:
            return None

        player_id = int(id_match.group(1))
        slug = href.rstrip("/").split("/")[-1] if "/" in href else ""

        # Helper to get text from cell by class
        def _cell_text(cls: str) -> str:
            el = row.select_one(f"td.{cls}")
            if not el:
                return ""
            return el.get_text(strip=True)

        def _cell_int(cls: str) -> Optional[int]:
            return _parse_int(_cell_text(cls))

        # Name: inside .table-name a, but the text also includes rating number
        # The actual player name is on the link title or from the slug
        name_cell = row.select_one("td.table-name")
        name = ""
        if name_cell:
            # Name is in the hover wrapper or directly in the link
            hover_el = name_cell.select_one("[title]")
            if hover_el and hover_el.get("title"):
                name = hover_el.get("title", "")
            if not name:
                # Fall back to slug-based name
                name = slug.replace("-", " ").title() if slug else ""

        rating = _cell_int("table-rating")

        # Position: main position and alt positions
        pos_cell = row.select_one("td.table-pos")
        position = ""
        if pos_cell:
            main_pos = pos_cell.select_one(".table-pos-main")
            position = main_pos.get_text(strip=True) if main_pos else pos_cell.get_text(strip=True).split("\n")[0].strip()

        # Price (PS — first .table-price.platform-ps-only)
        ps_price_cell = row.select_one("td.table-price.platform-ps-only")
        price_ps = None
        if ps_price_cell:
            price_el = ps_price_cell.select_one(".price")
            price_text = price_el.get_text(strip=True) if price_el else ps_price_cell.get_text(strip=True)
            price_ps = _parse_price(price_text)

        # Price (PC)
        pc_price_cell = row.select_one("td.table-price.platform-pc-only")
        price_pc = None
        if pc_price_cell:
            price_el = pc_price_cell.select_one(".price")
            price_text = price_el.get_text(strip=True) if price_el else pc_price_cell.get_text(strip=True)
            price_pc = _parse_price(price_text)

        # FUTBIN rating
        fb_rating_el = row.select_one(".futbin-rating-tag")
        futbin_rating = _parse_float(fb_rating_el.get_text(strip=True)) if fb_rating_el else None

        sm = _cell_int("table-skills")
        wf = _cell_int("table-weak-foot")
        pac = _cell_int("table-pace")
        sho = _cell_int("table-shooting")
        pas = _cell_int("table-passing")
        dri = _cell_int("table-dribbling")
        defense = _cell_int("table-defending")
        phy = _cell_int("table-physicality")
        popularity = _cell_int("table-popularity")
        igs = _cell_int("table-in-game-stats")

        return Player(
            id=player_id,
            name=name,
            rating=rating or 0,
            position=position,
            price_ps=price_ps,
            price_pc=price_pc,
            futbin_rating=futbin_rating,
            skill_moves=sm,
            weak_foot=wf,
            pac=pac,
            sho=sho,
            pas=pas,
            dri=dri,
            defense=defense,
            phy=phy,
            igs=igs,
            popularity=popularity,
            slug=slug,
            url=href,
        )

    # ── Player Detail (HTML Scraping) ─────────────────────────────────

    def get_player(self, player_id: int, slug: str = "") -> Optional[Player]:
        """Get detailed player info from the player page."""
        if not slug:
            # Try to find slug via search
            results = self.search_players(str(player_id))
            for r in results:
                if r.id == player_id:
                    slug = r.url.rstrip("/").split("/")[-1]
                    break
            if not slug:
                slug = str(player_id)

        path = f"/{DEFAULT_YEAR}/player/{player_id}/{slug}"
        soup = self._get_soup(path)

        # Extract basic info from the page
        name_el = soup.select_one("h1, .player-header-name")
        name = name_el.get_text(strip=True) if name_el else ""

        # Extract rating
        rating_el = soup.select_one(".playercard-26-rating, .player-card-rating")
        rating = _parse_int(rating_el.get_text(strip=True)) if rating_el else 0

        # Extract position
        pos_el = soup.select_one(".playercard-26-position")
        position = pos_el.get_text(strip=True) if pos_el else ""

        # Extract stats from the page info section
        stats = {}
        stat_rows = soup.select(".player-stat-row, .stat-row")
        for stat_row in stat_rows:
            label_el = stat_row.select_one(".stat-label, .stat-name")
            value_el = stat_row.select_one(".stat-value, .stat-number")
            if label_el and value_el:
                label = label_el.get_text(strip=True).lower()
                value = _parse_int(value_el.get_text(strip=True))
                stats[label] = value

        # Extract price from price box
        price_el = soup.select_one(".lowest-price-1, .price")
        price_ps = None
        if price_el:
            price_ps = _parse_price(price_el.get_text(strip=True))

        # Extract embedded ratings data
        ratings_script = soup.select_one("[data-futbin-ratings-data-script]")
        futbin_rating = None
        if ratings_script:
            try:
                ratings_data = json.loads(ratings_script.string)
                # Get top rating across positions
                for chem in ratings_data.get("ratingsPerChemistry", []):
                    for pos in chem.get("ratingsPerPosition", []):
                        for top in pos.get("topRatings", []):
                            r = top.get("rating", 0)
                            if futbin_rating is None or r > futbin_rating:
                                futbin_rating = r
            except (json.JSONDecodeError, TypeError):
                pass

        # Extract recent prices
        price_graph_el = soup.select_one("[data-recent-prices]")
        recent_prices_str = price_graph_el.get("data-recent-prices", "") if price_graph_el else ""

        return Player(
            id=player_id,
            name=name,
            rating=rating or 0,
            position=position,
            price_ps=price_ps,
            futbin_rating=futbin_rating,
            pac=stats.get("pac") or stats.get("pace"),
            sho=stats.get("sho") or stats.get("shooting"),
            pas=stats.get("pas") or stats.get("passing"),
            dri=stats.get("dri") or stats.get("dribbling"),
            defense=stats.get("def") or stats.get("defending"),
            phy=stats.get("phy") or stats.get("physicality"),
            slug=slug,
            url=f"/{DEFAULT_YEAR}/player/{player_id}/{slug}",
        )

    # ── Price History (HTML Scraping) ─────────────────────────────────

    def get_price_history(
        self, player_id: int, slug: str = "", platform: str = "ps"
    ) -> PriceHistory:
        """Get price history from the player prices page."""
        if not slug:
            slug = str(player_id)

        path = f"/{DEFAULT_YEAR}/player/{player_id}/{slug}/prices"
        soup = self._get_soup(path)

        # Extract name
        name_el = soup.select_one("h1, .player-header-name")
        name = name_el.get_text(strip=True) if name_el else ""

        # Find graph data — data-ps-data or data-pc-data attributes
        data_attr = f"data-{platform}-data"
        graph_els = soup.select(f"[{data_attr}]")

        prices = []
        # Use the first graph element (daily average)
        if graph_els:
            raw = graph_els[0].get(data_attr, "")
            try:
                data = json.loads(raw)
                for point in data:
                    if isinstance(point, list) and len(point) == 2:
                        prices.append(PricePoint(timestamp=point[0], price=point[1]))
            except (json.JSONDecodeError, TypeError):
                pass

        return PriceHistory(
            player_id=player_id,
            player_name=name,
            platform=platform,
            prices=prices,
        )

    # ── SBCs (HTML Scraping) ──────────────────────────────────────────

    def list_sbcs(self, category: Optional[str] = None) -> list[SBC]:
        """List Squad Building Challenges."""
        path = "/squad-building-challenges"
        if category:
            path = f"/squad-building-challenges/{category}"

        soup = self._get_soup(path)
        sbcs = []

        # Parse SBC entries
        sbc_cards = soup.select(".sbc-card, .sbc-row, .sbc-set, [class*='sbc']")
        seen_names = set()

        for card in sbc_cards:
            link = card.select_one("a[href*='squad-building-challenges']")
            if not link:
                continue

            name = link.get_text(strip=True)
            if not name or name in seen_names or len(name) > 100:
                continue
            seen_names.add(name)

            url = link.get("href", "")

            # Try to find cost info
            cost_el = card.select_one(".sbc-cost, .sbc-price, [class*='cost']")
            cost = cost_el.get_text(strip=True) if cost_el else ""

            # Try to find expiry info
            expire_el = card.select_one(".sbc-expire, .countdown, [class*='expire']")
            expires = expire_el.get_text(strip=True) if expire_el else ""

            sbcs.append(SBC(
                name=name,
                url=url,
                category=category or "",
                cost=cost,
                expires=expires,
            ))

        return sbcs

    def get_cheapest_by_rating(self) -> list[dict]:
        """Get cheapest players by rating for SBC fodder."""
        soup = self._get_soup("/squad-building-challenges/cheapest")
        results = []

        rows = soup.select("table tbody tr, .cheapest-row")
        for row in rows:
            cells = row.select("td")
            if len(cells) >= 2:
                rating = cells[0].get_text(strip=True)
                price = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                link = row.select_one("a[href*='/player/']")
                player_name = link.get_text(strip=True) if link else ""
                results.append({
                    "rating": rating,
                    "price": price,
                    "player": player_name,
                })

        return results

    # ── Market (HTML Scraping) ────────────────────────────────────────

    def get_market_index(self, rating: Optional[int] = None) -> list[MarketIndex]:
        """Get market index data."""
        path = f"/market/{rating}" if rating else "/market"
        soup = self._get_soup(path)

        # Try the HTMX index table endpoint
        indices = []

        # Parse from the page directly
        rows = soup.select("table tbody tr, .market-index-row")
        for row in rows:
            cells = row.select("td")
            link = row.select_one("a")
            name = link.get_text(strip=True) if link else ""
            if not name:
                continue

            # PS values
            ps_val = None
            ps_change = None
            pc_val = None
            pc_change = None

            ps_cells = row.select(".platform-ps-only")
            if ps_cells:
                ps_val = _parse_float(ps_cells[0].get_text(strip=True))
                if len(ps_cells) > 1:
                    change_text = ps_cells[1].get_text(strip=True).replace("%", "").strip()
                    ps_change = _parse_float(change_text)
                    if row.select_one(".day-change-negative.platform-ps-only"):
                        ps_change = -abs(ps_change) if ps_change else None

            pc_cells = row.select(".platform-pc-only")
            if pc_cells:
                pc_val = _parse_float(pc_cells[0].get_text(strip=True))
                if len(pc_cells) > 1:
                    change_text = pc_cells[1].get_text(strip=True).replace("%", "").strip()
                    pc_change = _parse_float(change_text)
                    if row.select_one(".day-change-negative.platform-pc-only"):
                        pc_change = -abs(pc_change) if pc_change else None

            indices.append(MarketIndex(
                name=name,
                value_ps=ps_val,
                value_pc=pc_val,
                change_pct_ps=ps_change,
                change_pct_pc=pc_change,
            ))

        return indices

    # ── Evolutions (HTML Scraping) ────────────────────────────────────

    def list_evolutions(
        self, category: Optional[str] = None, expiring: bool = False
    ) -> list[Evolution]:
        """List evolutions."""
        params = {}
        if expiring:
            params["last_chance"] = "true"
        else:
            params["last_chance"] = "false"
        if category:
            params["category"] = category

        soup = self._get_soup("/evolutions", params=params)
        evolutions = []

        # Parse evolution cards
        cards = soup.select("a[href*='/evolutions/'], .evolution-card, .evo-card")
        seen = set()
        for card in cards:
            href = card.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            name = card.get_text(strip=True)
            if not name or len(name) > 80:
                name_el = card.select_one(".evo-name, h3, h4, .title")
                name = name_el.get_text(strip=True) if name_el else href.split("/")[-1]

            expire_el = card.select_one(".countdown, [class*='expire']")
            expires = expire_el.get_text(strip=True) if expire_el else ""

            evolutions.append(Evolution(
                name=name,
                url=href,
                category=category or "",
                expires=expires,
            ))

        return evolutions

    # ── Popular / Latest (HTML Scraping) ──────────────────────────────

    def get_popular_players(self) -> list[Player]:
        """Get popular players."""
        soup = self._get_soup("/popular")
        return self._parse_player_table(soup)

    def get_latest_players(self) -> list[Player]:
        """Get latest added players."""
        soup = self._get_soup("/latest")
        return self._parse_player_table(soup)
