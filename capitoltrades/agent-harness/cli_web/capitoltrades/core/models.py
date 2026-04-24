"""HTML parsing → structured dict converters.

capitoltrades.com renders all data server-side as HTML. These functions
extract typed dicts from BeautifulSoup documents.
"""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from .exceptions import NotFoundError

_ID_TRADE = re.compile(r"/trades/(\d+)")
_ID_POLITICIAN = re.compile(r"/politicians/([A-Z]\d+)")
_ID_ISSUER = re.compile(r"/issuers/(\d+)")
_NUM_WITH_COMMAS = re.compile(r"\d{1,3}(?:,\d{3})+|\d+")
_MONEY = re.compile(r"\$?([\d,]+(?:\.\d+)?)\s*([KMB]?)")


def _txt(node: Tag | None) -> str:
    if node is None:
        return ""
    return node.get_text(" ", strip=True)


def _extract_href_id(node: Tag | None, pattern: re.Pattern) -> str | None:
    if node is None:
        return None
    href = node.get("href") or ""
    m = pattern.search(href)
    return m.group(1) if m else None


def _parse_money(text: str) -> float | None:
    """Parse money strings like '29.81M', '$2.312B', '1.38K'."""
    if not text:
        return None
    m = _MONEY.search(text)
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    suffix = m.group(2)
    mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(suffix, 1.0)
    return num * mult


def _parse_int_loose(text: str) -> int | None:
    """Parse '1,201' -> 1201, '26' -> 26."""
    if not text:
        return None
    m = _NUM_WITH_COMMAS.search(text)
    if not m:
        return None
    return int(m.group(0).replace(",", ""))


# ─── Trades ─────────────────────────────────────────────────────────────────

def parse_trades_list(soup: BeautifulSoup) -> list[dict]:
    """Parse the trades list table on /trades.

    Main trades table columns: Politician, Traded Issuer, Published, Traded,
    Filed After, Owner, Type, Size, Price (9 data columns + 1 action column).

    Also handles subset tables on politician/issuer detail pages which use
    a reduced column set (7 columns).
    """
    table = soup.find("table")
    if table is None:
        return []
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    # Header-based column mapping — robust to column-count variations
    header_cells = rows[0].find_all("th")
    header_names = [_txt(th).lower() for th in header_cells]

    def col_idx(*candidates: str) -> int | None:
        for c in candidates:
            for i, name in enumerate(header_names):
                if c in name:
                    return i
        return None

    idx_pol = col_idx("politician")
    idx_issuer = col_idx("traded issuer", "issuer")
    idx_pub = col_idx("published")
    idx_traded = col_idx("traded")
    if idx_traded == idx_issuer:  # "traded issuer" matched
        idx_traded = col_idx("^traded$")
        if idx_traded is None:
            # Find traded that isn't the issuer column
            for i, name in enumerate(header_names):
                if name.strip() == "traded":
                    idx_traded = i
                    break
    idx_filed = col_idx("filed")
    idx_owner = col_idx("owner")
    idx_type = col_idx("type")
    idx_size = col_idx("size")
    idx_price = col_idx("price")

    def cell_at(cells, idx):
        if idx is None or idx >= len(cells):
            return None
        return cells[idx]

    out: list[dict] = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue

        # Link to trade detail (action column)
        trade_link = row.find("a", href=_ID_TRADE)
        trade_id = _extract_href_id(trade_link, _ID_TRADE)

        pol_cell = cell_at(cells, idx_pol)
        pol_link = pol_cell.find("a", href=_ID_POLITICIAN) if pol_cell else None
        politician_id = _extract_href_id(pol_link, _ID_POLITICIAN)

        pol_name_el = pol_cell.find("h2") or pol_cell.find("h3") if pol_cell else None
        politician_name = _txt(pol_name_el) if pol_name_el else (_txt(pol_link) if pol_link else None)

        party_el = pol_cell.find("span", class_=re.compile(r"party--")) if pol_cell else None
        chamber_el = pol_cell.find("span", class_=re.compile(r"chamber--")) if pol_cell else None
        state_el = pol_cell.find("span", class_=re.compile(r"us-state")) if pol_cell else None

        issuer_cell = cell_at(cells, idx_issuer)
        issuer_link = issuer_cell.find("a", href=_ID_ISSUER) if issuer_cell else None
        issuer_id = _extract_href_id(issuer_link, _ID_ISSUER)
        issuer_name_el = issuer_cell.find("h3") if issuer_cell else None
        issuer_name = _txt(issuer_name_el) if issuer_name_el else (_txt(issuer_link) if issuer_link else None)
        ticker_label = None
        if issuer_cell:
            # Main list uses <span class="q-field issuer-ticker">, detail cards use q-label
            tkr = issuer_cell.find(class_=re.compile(r"issuer-ticker|q-label"))
            if tkr:
                ticker_label = _txt(tkr)

        published = _txt(cell_at(cells, idx_pub))
        traded = _txt(cell_at(cells, idx_traded))
        filed_after = _txt(cell_at(cells, idx_filed))
        owner = _txt(cell_at(cells, idx_owner))
        tx_type = _txt(cell_at(cells, idx_type))
        size = (_txt(cell_at(cells, idx_size)) or "").replace("\xa0", " ").strip()
        price = _txt(cell_at(cells, idx_price))

        out.append({
            "trade_id": trade_id,
            "politician_id": politician_id,
            "politician_name": politician_name,
            "politician_party": _txt(party_el) or None,
            "politician_chamber": _txt(chamber_el) or None,
            "politician_state": _txt(state_el) or None,
            "issuer_id": issuer_id,
            "issuer_name": issuer_name,
            "ticker": ticker_label,
            "published": published or None,
            "traded": traded or None,
            "filed_after_days": filed_after or None,
            "owner": owner or None,
            "tx_type": tx_type or None,
            "size": size or None,
            "price": price or None,
        })
    return out


def parse_trade_detail(soup: BeautifulSoup, trade_id: str) -> dict:
    """Parse a /trades/{id} detail page (the q-detail-card article)."""
    title = _txt(soup.find("title"))
    # The detail card article
    card = soup.find("article", class_=re.compile(r"transaction-detail-card"))
    if card is None:
        card = soup

    # Trade size from the h1 inside the header
    h1 = card.find("h1")
    trade_size = _txt(h1) if h1 else None

    # tx-type span
    tx_type_el = card.find("span", class_=re.compile(r"^q-field tx-type"))
    tx_type = _txt(tx_type_el) if tx_type_el else None

    # party / chamber / state spans
    party_el = card.find("span", class_=re.compile(r"party--"))
    chamber_el = card.find("span", class_=re.compile(r"chamber--"))
    state_el = card.find("span", class_=re.compile(r"us-state-full--"))

    # Politician link (under cell--politician)
    pol_cell = card.find("div", class_=re.compile(r"cell--politician"))
    pol_link = pol_cell.find("a", href=_ID_POLITICIAN) if pol_cell else None
    politician_id = _extract_href_id(pol_link, _ID_POLITICIAN)
    politician_name = _txt(pol_link) if pol_link else None

    # Issuer link
    issuer_cell = card.find("div", class_=re.compile(r"cell--issuer"))
    issuer_link = issuer_cell.find("a", href=_ID_ISSUER) if issuer_cell else None
    issuer_id = _extract_href_id(issuer_link, _ID_ISSUER)
    issuer_name = _txt(issuer_link) if issuer_link else None
    ticker = None
    if issuer_cell:
        label = issuer_cell.find("div", class_=re.compile(r"q-label"))
        ticker = _txt(label) if label else None

    # Traded / Published dates
    def _cell_value(cell_class: str) -> str | None:
        cell = card.find("div", class_=re.compile(cell_class))
        if not cell:
            return None
        val = cell.find("div", class_=re.compile(r"q-value"))
        return _txt(val) if val else None

    traded = _cell_value(r"cell--tx-date")
    published = _cell_value(r"cell--pub-date")

    # Additional label/value pairs from flex containers
    extras: dict[str, str] = {}
    for extra in card.find_all("div", class_=re.compile(r"^flex flex-col justify-between")):
        spans = extra.find_all("span")
        if len(spans) >= 2:
            value = _txt(spans[0])
            label = _txt(spans[1]).lower().replace(" ", "_")
            if label and value:
                extras[label] = value

    # Comment / filing link
    comment_el = card.find("div", class_=re.compile(r"trade-comment"))
    comment = _txt(comment_el.find("q")) if comment_el and comment_el.find("q") else None

    filing_el = card.find("div", class_=re.compile(r"view-filing"))
    filing_url = None
    if filing_el:
        a = filing_el.find("a")
        if a:
            filing_url = a.get("href")

    return {
        "trade_id": trade_id,
        "title": title,
        "tx_type": tx_type,
        "size": trade_size,
        "politician_id": politician_id,
        "politician_name": politician_name,
        "politician_party": _txt(party_el) or None,
        "politician_chamber": _txt(chamber_el) or None,
        "politician_state": _txt(state_el) or None,
        "issuer_id": issuer_id,
        "issuer_name": issuer_name,
        "ticker": ticker,
        "traded": traded,
        "published": published,
        "owner": extras.get("owner"),
        "asset_type": extras.get("asset_type"),
        "price": extras.get("price"),
        "shares": extras.get("shares"),
        "filed_on": extras.get("filed_on"),
        "reporting_gap": extras.get("reporting_gap"),
        "comment": comment,
        "filing_url": filing_url,
    }


# ─── Politicians ────────────────────────────────────────────────────────────

def parse_politicians_list(soup: BeautifulSoup) -> list[dict]:
    """Parse /politicians list of cards."""
    links = soup.select('a[href^="/politicians/"]')
    seen: set[str] = set()
    out: list[dict] = []
    for link in links:
        pid = _extract_href_id(link, _ID_POLITICIAN)
        if not pid or pid in seen:
            continue
        seen.add(pid)
        text = _txt(link)
        tokens = text.split()

        # Best-effort parse: "<name> <party> <state> Trades <n> Issuers <n> Volume <v> Last Traded <date>"
        name = None
        party = None
        state = None
        trades_count = None
        issuers_count = None
        volume = None
        last_traded = None

        # Find anchors for known labels
        try:
            name_parts = []
            i = 0
            while i < len(tokens) and tokens[i] not in ("Democrat", "Republican", "Independent", "Other"):
                name_parts.append(tokens[i])
                i += 1
            name = " ".join(name_parts) if name_parts else None
            if i < len(tokens):
                party = tokens[i]
                i += 1
            # State may be multi-word (e.g., "New Hampshire")
            state_parts = []
            while i < len(tokens) and tokens[i] not in ("Trades", "Issuer", "Issuers", "Volume"):
                state_parts.append(tokens[i])
                i += 1
            state = " ".join(state_parts) if state_parts else None

            for j, tok in enumerate(tokens):
                if tok in ("Trades",) and j + 1 < len(tokens):
                    trades_count = _parse_int_loose(tokens[j + 1])
                elif tok in ("Issuers", "Issuer") and j + 1 < len(tokens):
                    issuers_count = _parse_int_loose(tokens[j + 1])
                elif tok == "Volume" and j + 1 < len(tokens):
                    volume = tokens[j + 1]
                elif tok == "Last" and j + 2 < len(tokens) and tokens[j + 1] == "Traded":
                    last_traded = tokens[j + 2]
        except Exception:
            pass

        out.append({
            "politician_id": pid,
            "name": name,
            "party": party,
            "state": state,
            "trades_count": trades_count,
            "issuers_count": issuers_count,
            "volume": volume,
            "last_traded": last_traded,
            "raw_text": text,
        })
    return out


def parse_politician_detail(soup: BeautifulSoup, politician_id: str) -> dict:
    """Parse /politicians/{id} detail page (with trade history table)."""
    title = _txt(soup.find("title"))
    h1 = soup.find("h1")
    name = _txt(h1) if h1 else None

    # Get the trade history table. The reduced columns don't include politician
    # info — back-fill from the page identity.
    trades = parse_trades_list(soup)
    for t in trades:
        if t.get("politician_id") is None:
            t["politician_id"] = politician_id
        if t.get("politician_name") is None and name:
            t["politician_name"] = name

    # Get any summary stats from .q-stat or similar
    stats: dict[str, Any] = {}
    main = soup.find("main") or soup
    for stat in main.select("[class*='q-stat'], figure + div, [class*='stat-card']"):
        label_el = stat.find(class_=re.compile(r"label|title"))
        value_el = stat.find(class_=re.compile(r"value|stat-value"))
        if label_el and value_el:
            stats[_txt(label_el).lower()] = _txt(value_el)

    return {
        "politician_id": politician_id,
        "name": name,
        "title": title,
        "stats": stats or None,
        "recent_trades": trades,
    }


# ─── Issuers ────────────────────────────────────────────────────────────────

def parse_issuers_list(soup: BeautifulSoup) -> list[dict]:
    """Parse /issuers list of cards."""
    links = soup.select('a[href^="/issuers/"]')
    seen: set[str] = set()
    out: list[dict] = []
    for link in links:
        iid = _extract_href_id(link, _ID_ISSUER)
        if not iid or iid in seen:
            continue
        seen.add(iid)
        # Find parent card for full text context
        parent = link.find_parent("div")
        card_text = _txt(parent) if parent else _txt(link)
        ticker_el = (parent or link).find("span", class_=re.compile("ticker"))
        name_el = link.find("h3") or link
        out.append({
            "issuer_id": iid,
            "name": _txt(name_el),
            "ticker": _txt(ticker_el) if ticker_el else None,
            "card_text": card_text[:300],
        })
    return out


def parse_issuer_detail(soup: BeautifulSoup, issuer_id: str) -> dict:
    """Parse /issuers/{id} detail page."""
    title = _txt(soup.find("title"))
    h1 = soup.find("h1")
    name = _txt(h1) if h1 else None
    trades = parse_trades_list(soup)
    # Back-fill issuer info (not present in reduced-column table)
    for t in trades:
        if t.get("issuer_id") is None:
            t["issuer_id"] = issuer_id
        if t.get("issuer_name") is None and name:
            t["issuer_name"] = name
    return {
        "issuer_id": issuer_id,
        "name": name,
        "title": title,
        "recent_trades": trades,
    }


# ─── Articles ───────────────────────────────────────────────────────────────

_DATE_HINT = re.compile(
    r"^(?:Today|Yesterday|\d+\s+(?:mins?|hours?|days?|weeks?|months?)\s+ago|"
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|"
    r"\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)


def _parse_content_list(soup: BeautifulSoup, kind: str) -> list[dict]:
    """Generic parser for /articles, /buzz, /press — all use the same card layout."""
    out: list[dict] = []
    seen: set[str] = set()
    prefix = f"/{kind}/"
    for link in soup.select(f'a[href^="{prefix}"]'):
        href = link.get("href") or ""
        if not href.startswith(prefix):
            continue
        slug = href.replace(prefix, "", 1).split("?")[0].strip("/")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        h3 = link.find("h3") or link.find("h2")
        title = _txt(h3) if h3 else _txt(link)

        # Date hunt: explicit class first, then Tailwind muted span, then any span
        # whose text matches a date-like pattern.
        date_el = link.find("span", class_=re.compile(r"date|time|published"))
        date_text = _txt(date_el) if date_el else None
        if not date_text:
            for span in link.find_all("span"):
                t = _txt(span)
                if t and _DATE_HINT.match(t) and t not in (title or ""):
                    date_text = t
                    break

        out.append({
            "slug": slug,
            "title": title,
            "published": date_text or None,
            "url": f"https://www.capitoltrades.com{prefix}{slug}",
        })
    return out


def _parse_content_detail(soup: BeautifulSoup, slug: str, kind: str) -> dict:
    """Generic parser for /articles/{slug}, /buzz/{slug}, /press/{slug}."""
    h1 = soup.find("h1")
    title = _txt(h1) if h1 else _txt(soup.find("title"))
    article = soup.find("article") or soup.find("main") or soup
    for tag in article.find_all(["nav", "header", "footer", "aside", "script", "style"]):
        tag.decompose()
    paragraphs = [_txt(p) for p in article.find_all("p") if _txt(p)]
    body = "\n\n".join(paragraphs)
    time_el = article.find("time")
    published = (time_el.get("datetime") if time_el else None) or _txt(time_el)
    return {
        "slug": slug,
        "title": title,
        "published": published,
        "body": body,
        "url": f"https://www.capitoltrades.com/{kind}/{slug}",
    }


def parse_articles_list(soup: BeautifulSoup) -> list[dict]:
    """Parse /articles list."""
    return _parse_content_list(soup, "articles")


def parse_article_detail(soup: BeautifulSoup, slug: str) -> dict:
    """Parse /articles/{slug} detail page."""
    return _parse_content_detail(soup, slug, "articles")


def parse_buzz_list(soup: BeautifulSoup) -> list[dict]:
    """Parse /buzz list of third-party stock-market news snippets."""
    return _parse_content_list(soup, "buzz")


def parse_buzz_detail(soup: BeautifulSoup, slug: str) -> dict:
    """Parse /buzz/{slug} detail page."""
    return _parse_content_detail(soup, slug, "buzz")


def parse_press_list(soup: BeautifulSoup) -> list[dict]:
    """Parse /press list of press coverage."""
    return _parse_content_list(soup, "press")


def parse_press_detail(soup: BeautifulSoup, slug: str) -> dict:
    """Parse /press/{slug} detail page."""
    return _parse_content_detail(soup, slug, "press")


# ─── Stats ──────────────────────────────────────────────────────────────────

def parse_trades_stats(soup: BeautifulSoup) -> dict:
    """Parse the top stats cards on /trades (total trades, volume, politicians, issuers)."""
    stats: dict[str, Any] = {}
    # The stats cards are divs with a big number + label
    # Find all text that looks like stats
    page_text = soup.get_text(" ", strip=True)
    # Known labels
    known = ["Trades", "Filings", "Volume", "Politicians", "Issuers"]
    # Find all numbers adjacent to these labels
    for label in known:
        pattern = re.compile(r"(\$?\d[\d,.]*[KMB]?)\s*" + label + r"\b")
        m = pattern.search(page_text)
        if m:
            stats[label.lower()] = m.group(1)
    return stats
