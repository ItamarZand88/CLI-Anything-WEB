"""Unit tests for core modules (no network).

Covers:
- Exception hierarchy + HTTP status mapping
- HTML parsers (trades list, trade detail, politician list, issuer list, articles)
- Helpers (handle_errors, print_json, ensure_utf8)
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from cli_web.capitoltrades.core.exceptions import (
    AuthError,
    CapitoltradesError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServerError,
    raise_for_status,
)
from cli_web.capitoltrades.core.models import (
    parse_article_detail,
    parse_articles_list,
    parse_buzz_detail,
    parse_buzz_list,
    parse_issuer_detail,
    parse_issuers_list,
    parse_politician_detail,
    parse_politicians_list,
    parse_press_detail,
    parse_press_list,
    parse_trade_detail,
    parse_trades_list,
    parse_trades_stats,
)


# ─── Exception hierarchy ────────────────────────────────────────────────────

class TestExceptions:
    def test_auth_error_on_401(self):
        resp = MagicMock(status_code=401, text="Unauthorized", headers={})
        with pytest.raises(AuthError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.recoverable is True

    def test_auth_error_on_403(self):
        resp = MagicMock(status_code=403, text="Forbidden", headers={})
        with pytest.raises(AuthError):
            raise_for_status(resp)

    def test_not_found_on_404(self):
        resp = MagicMock(status_code=404, text="Not Found", headers={})
        with pytest.raises(NotFoundError):
            raise_for_status(resp)

    def test_rate_limit_with_retry_after(self):
        resp = MagicMock(status_code=429, text="Too Many Requests")
        resp.headers = {"Retry-After": "30"}
        with pytest.raises(RateLimitError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.retry_after == 30.0

    def test_rate_limit_without_retry_after(self):
        resp = MagicMock(status_code=429, text="429")
        resp.headers = {}
        with pytest.raises(RateLimitError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.retry_after is None

    def test_server_error_on_5xx(self):
        resp = MagicMock(status_code=503, text="Service Unavailable", headers={})
        with pytest.raises(ServerError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.status_code == 503

    def test_no_raise_on_2xx(self):
        resp = MagicMock(status_code=200, text="ok")
        raise_for_status(resp)  # Should not raise

    def test_error_to_dict_has_code(self):
        err = NotFoundError("missing").to_dict()
        assert err["error"] is True
        assert err["code"] == "NOT_FOUND"
        assert "missing" in err["message"]

    def test_auth_error_to_dict_code(self):
        err = AuthError("expired").to_dict()
        assert err["code"] == "AUTH_EXPIRED"

    def test_rate_limit_to_dict_includes_retry_after(self):
        err = RateLimitError("too many", retry_after=60).to_dict()
        assert err["code"] == "RATE_LIMITED"
        assert err["retry_after"] == 60


# ─── HTML Parsers — trades list ─────────────────────────────────────────────

_TRADES_TABLE_HTML = """
<html><body>
<table>
  <thead>
    <tr>
      <th>Politician</th><th>Traded Issuer</th><th>Published</th>
      <th>Traded</th><th>Filed After</th><th>Owner</th>
      <th>Type</th><th>Size</th><th>Price</th><th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <div class="q-cell cell--politician">
          <figure></figure>
          <div>
            <h2><a href="/politicians/S000168">Maria Elvira Salazar</a></h2>
            <div>
              <span class="q-field party party--republican">Republican</span>
              <span class="q-field chamber chamber--house">House</span>
              <span class="q-field us-state us-state--fl">FL</span>
            </div>
          </div>
        </div>
      </td>
      <td>
        <div class="q-cell cell--traded-issuer">
          <figure></figure>
          <div>
            <h3 class="issuer-name"><a href="/issuers/429725">Amgen Inc</a></h3>
            <span class="q-field issuer-ticker">AMGN:US</span>
          </div>
        </div>
      </td>
      <td>13:05 Yesterday</td>
      <td>24 Mar 2026</td>
      <td>days 28</td>
      <td>Undisclosed</td>
      <td><span class="q-field tx-type tx-type--buy">buy</span></td>
      <td><span class="q-field trade-value">15K&ndash;50K</span></td>
      <td>$348.43</td>
      <td><a href="/trades/20003797393">Goto</a></td>
    </tr>
  </tbody>
</table>
</body></html>
"""


class TestTradesListParser:
    def test_parses_one_row(self):
        soup = BeautifulSoup(_TRADES_TABLE_HTML, "html.parser")
        rows = parse_trades_list(soup)
        assert len(rows) == 1
        r = rows[0]
        assert r["trade_id"] == "20003797393"
        assert r["politician_id"] == "S000168"
        assert r["politician_name"] == "Maria Elvira Salazar"
        assert r["politician_party"] == "Republican"
        assert r["politician_chamber"] == "House"
        assert r["issuer_id"] == "429725"
        assert r["issuer_name"] == "Amgen Inc"
        assert r["ticker"] == "AMGN:US"
        assert r["tx_type"] == "buy"
        assert r["traded"] == "24 Mar 2026"
        assert r["price"] == "$348.43"
        assert "50K" in r["size"]
        assert r["filed_after_days"] == "days 28"
        assert r["owner"] == "Undisclosed"

    def test_empty_table_returns_empty_list(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        assert parse_trades_list(soup) == []

    def test_reduced_column_table_on_detail_page(self):
        """Politician/issuer detail pages use a 7-column table (no politician col)."""
        html = """
        <table>
          <thead><tr>
            <th>Traded Issuer</th><th>Published</th><th>Traded</th>
            <th>Filed After</th><th>Type</th><th>Size</th><th></th>
          </tr></thead>
          <tbody><tr>
            <td>
              <h3><a href="/issuers/435544">US TREASURY BILLS</a></h3>
              <span class="q-field issuer-ticker">--</span>
            </td>
            <td>1 Apr 2026</td><td>20 Mar 2026</td><td>days 12</td>
            <td><span class="tx-type tx-type--buy">buy</span></td>
            <td><span class="q-field trade-value">15K-50K</span></td>
            <td><a href="/trades/20003790000">Goto</a></td>
          </tr></tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_trades_list(soup)
        assert len(rows) == 1
        assert rows[0]["trade_id"] == "20003790000"
        assert rows[0]["issuer_id"] == "435544"
        assert rows[0]["tx_type"] == "buy"
        # No politician columns in this table
        assert rows[0]["politician_id"] is None


# ─── Trade detail ───────────────────────────────────────────────────────────

_TRADE_DETAIL_HTML = """
<html><body>
<title>Maria Elvira Salazar bought Amgen Inc</title>
<article class="transaction-detail-card tx-type--buy">
  <header>
    <figure class="trade-logo trade-logo--tx-type-buy">
      <span class="q-field tx-type tx-type--buy">buy</span>
    </figure>
    <h1><span class="q-field trade-value">15K-50K</span></h1>
  </header>
  <section>
    <div class="q-cell cell--politician">
      <div class="q-label">
        <span class="q-field party party--republican">Republican</span>
        <span class="q-field chamber chamber--house">House</span>
        <span class="q-field us-state-full us-state-full--fl">Florida</span>
      </div>
      <div class="q-value"><a href="/politicians/S000168">Maria Elvira Salazar</a></div>
    </div>
    <div class="q-cell cell--issuer">
      <div class="q-label">AMGN:US</div>
      <div class="q-value"><a href="/issuers/429725">Amgen Inc</a></div>
    </div>
    <div class="q-cell cell--tx-date">
      <div class="q-label">Traded</div>
      <div class="q-value"><span>2026-03-24</span></div>
    </div>
    <div class="q-cell cell--pub-date">
      <div class="q-label">Published</div>
      <div class="q-value"><span>2026-04-22</span></div>
    </div>
    <div class="flex flex-col justify-between">
      <span>Undisclosed</span><span>Owner</span>
    </div>
    <div class="flex flex-col justify-between">
      <span>Stock</span><span>Asset Type</span>
    </div>
    <div class="flex flex-col justify-between">
      <span>348.43</span><span>Price</span>
    </div>
    <div class="flex flex-col justify-between">
      <span>44 - 144</span><span>Shares</span>
    </div>
    <div class="trade-comment">
      <q>Subholding Of: UBS IRA Account</q>
    </div>
    <div class="view-filing">
      <a href="https://disclosures.example.com/filing.pdf">View</a>
    </div>
  </section>
</article>
</body></html>
"""


class TestTradeDetailParser:
    def test_parses_all_fields(self):
        soup = BeautifulSoup(_TRADE_DETAIL_HTML, "html.parser")
        data = parse_trade_detail(soup, "20003797393")
        assert data["trade_id"] == "20003797393"
        assert data["tx_type"] == "buy"
        assert "50K" in data["size"]
        assert data["politician_id"] == "S000168"
        assert data["politician_name"] == "Maria Elvira Salazar"
        assert data["politician_party"] == "Republican"
        assert data["politician_chamber"] == "House"
        assert data["politician_state"] == "Florida"
        assert data["issuer_id"] == "429725"
        assert data["issuer_name"] == "Amgen Inc"
        assert data["ticker"] == "AMGN:US"
        assert data["traded"] == "2026-03-24"
        assert data["published"] == "2026-04-22"
        assert data["owner"] == "Undisclosed"
        assert data["asset_type"] == "Stock"
        assert data["price"] == "348.43"
        assert data["shares"] == "44 - 144"
        assert "UBS" in (data["comment"] or "")
        assert data["filing_url"].startswith("https://")


# ─── Politicians / issuers / articles lists ──────────────────────────────────

class TestListParsers:
    def test_politicians_list_extracts_cards(self):
        html = """
        <main><main>
          <a href="/politicians/Y000067">
            <div>Rudy Yakym Republican Indiana Trades 26 Issuers 1 Volume 1.38M Last Traded 2026-04-06</div>
          </a>
          <a href="/politicians/C001123">
            <div>Gil Cisneros Democrat California Trades 1,201 Issuers 461 Volume 29.81M Last Traded 2026-03-31</div>
          </a>
        </main></main>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_politicians_list(soup)
        assert len(rows) == 2
        assert rows[0]["politician_id"] == "Y000067"
        assert "Rudy" in rows[0]["name"]
        assert rows[0]["party"] == "Republican"
        assert rows[0]["state"] == "Indiana"
        assert rows[0]["trades_count"] == 26
        assert rows[1]["politician_id"] == "C001123"
        assert rows[1]["party"] == "Democrat"
        assert rows[1]["trades_count"] == 1201

    def test_politicians_list_deduplicates(self):
        """Same politician id appearing twice — only one entry returned."""
        html = """
        <main>
          <a href="/politicians/Y000067"><div>Rudy Yakym Republican Indiana</div></a>
          <a href="/politicians/Y000067"><div>Rudy Yakym (again)</div></a>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_politicians_list(soup)
        assert len(rows) == 1

    def test_issuers_list_extracts_cards(self):
        html = """
        <main>
          <a href="/issuers/435544"><h3>US TREASURY BILLS</h3></a>
          <a href="/issuers/433382">
            <h3>Microsoft Corp</h3>
            <span class="issuer-ticker">MSFT:US</span>
          </a>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_issuers_list(soup)
        assert len(rows) == 2
        assert rows[0]["issuer_id"] == "435544"
        assert rows[0]["name"] == "US TREASURY BILLS"
        assert rows[1]["issuer_id"] == "433382"
        assert rows[1]["name"] == "Microsoft Corp"

    def test_buzz_list_parses_tailwind_muted_date(self):
        """Buzz cards put the date in a Tailwind <span class="text-muted-...">, not a 'date' class."""
        html = """
        <main>
          <a href="/buzz/test-slug-1-2026-04-23">
            <article>
              <span class="text-size-3 text-muted-foreground">Yesterday</span>
              <h3>Test buzz title</h3>
            </article>
          </a>
          <a href="/buzz/another-2026-04-16">
            <article>
              <span class="text-size-3 text-muted-foreground">7 days ago</span>
              <h3>Another buzz</h3>
            </article>
          </a>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_buzz_list(soup)
        assert len(rows) == 2
        assert rows[0]["slug"] == "test-slug-1-2026-04-23"
        assert rows[0]["published"] == "Yesterday"
        assert "Test buzz title" in rows[0]["title"]
        assert rows[0]["url"].endswith(rows[0]["slug"])
        assert rows[1]["published"] == "7 days ago"

    def test_press_list_parses_dated_entries(self):
        html = """
        <main>
          <a href="/press/pelosi-mumbles-2026-03-05">
            <span class="text-muted-foreground">25 February 2026</span>
            <h3>Nancy Pelosi mumbles</h3>
          </a>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_press_list(soup)
        assert len(rows) == 1
        assert rows[0]["slug"] == "pelosi-mumbles-2026-03-05"
        assert rows[0]["published"] == "25 February 2026"

    def test_buzz_detail_has_body(self):
        html = """
        <html><body>
          <article>
            <h1>Anthropic now requires ID verification</h1>
            <p>Paragraph one of the buzz.</p>
            <p>Paragraph two.</p>
          </article>
        </body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        data = parse_buzz_detail(soup, "anthropic-id-verification")
        assert data["slug"] == "anthropic-id-verification"
        assert "Anthropic" in data["title"]
        assert "Paragraph one" in data["body"]
        assert "/buzz/" in data["url"]

    def test_press_detail_has_body(self):
        html = """
        <html><body><article>
          <h1>Stock trading panel member sold UnitedHealth</h1>
          <p>Press article body.</p>
        </article></body></html>
        """
        soup = BeautifulSoup(html, "html.parser")
        data = parse_press_detail(soup, "stock-trading-2026-02-04")
        assert data["title"].startswith("Stock")
        assert data["body"].startswith("Press")
        assert "/press/" in data["url"]

    def test_articles_list_extracts_slugs(self):
        html = """
        <main>
          <a href="/articles/defense-stocks-2026-04-23">
            <span class="date">Today, 10:20</span>
            <h3>A Foreign Affairs Committee Member Just Bought Defense Stocks</h3>
          </a>
          <a href="/articles/supreme-court-tariffs-2026-04-21">
            <span class="date">2 days ago</span>
            <h3>Supreme Court Strikes Down Trump's IEEPA Tariffs</h3>
          </a>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        rows = parse_articles_list(soup)
        assert len(rows) == 2
        assert rows[0]["slug"] == "defense-stocks-2026-04-23"
        assert "Defense Stocks" in rows[0]["title"]
        assert rows[0]["published"] == "Today, 10:20"
        assert rows[0]["url"].endswith(rows[0]["slug"])


# ─── Stats ──────────────────────────────────────────────────────────────────

class TestStatsParser:
    def test_extracts_overview_numbers(self):
        html = """
        <main>
          <div>
            <div>35,384</div><div>Trades</div>
            <div>1,739</div><div>Filings</div>
            <div>$2.312B</div><div>Volume</div>
            <div>198</div><div>Politicians</div>
            <div>3,057</div><div>Issuers</div>
          </div>
        </main>
        """
        soup = BeautifulSoup(html, "html.parser")
        stats = parse_trades_stats(soup)
        assert stats.get("trades") == "35,384"
        assert stats.get("volume") == "$2.312B"
        assert stats.get("politicians") == "198"


# ─── Helpers ────────────────────────────────────────────────────────────────

class TestHelpers:
    def test_handle_errors_auth_exits_1(self):
        from cli_web.capitoltrades.utils.helpers import handle_errors
        with pytest.raises(SystemExit) as exc:
            with handle_errors(json_mode=False):
                raise AuthError("expired")
        assert exc.value.code == 1

    def test_handle_errors_not_found_exits_1(self):
        from cli_web.capitoltrades.utils.helpers import handle_errors
        with pytest.raises(SystemExit) as exc:
            with handle_errors(json_mode=False):
                raise NotFoundError("missing")
        assert exc.value.code == 1

    def test_handle_errors_unknown_exits_2(self):
        from cli_web.capitoltrades.utils.helpers import handle_errors
        with pytest.raises(SystemExit) as exc:
            with handle_errors(json_mode=False):
                raise ValueError("bug")
        assert exc.value.code == 2

    def test_handle_errors_json_mode_outputs_json(self, capsys):
        from cli_web.capitoltrades.utils.helpers import handle_errors
        with pytest.raises(SystemExit):
            with handle_errors(json_mode=True):
                raise NotFoundError("missing trade 99")
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["error"] is True
        assert data["code"] == "NOT_FOUND"
        assert "missing trade 99" in data["message"]


# ─── Client mocking ─────────────────────────────────────────────────────────

class TestClientMocked:
    def test_get_html_wraps_network_error(self):
        from cli_web.capitoltrades.core.client import CapitoltradesClient
        with patch("cli_web.capitoltrades.core.client.curl_requests.Session") as session_cls:
            session = MagicMock()
            session.request.side_effect = RuntimeError("connection refused")
            session_cls.return_value = session
            with pytest.raises(NetworkError):
                CapitoltradesClient().get_html("/trades")

    def test_get_bff_json_parses_response(self):
        from cli_web.capitoltrades.core.client import CapitoltradesClient
        with patch("cli_web.capitoltrades.core.client.curl_requests.Session") as session_cls:
            session = MagicMock()
            resp = MagicMock(status_code=200, text='{"data":[]}')
            resp.json = lambda: {"data": [], "meta": {}}
            session.request.return_value = resp
            session_cls.return_value = session
            result = CapitoltradesClient().get_bff_json("/issuers", params={"search": "test"})
            assert result == {"data": [], "meta": {}}
