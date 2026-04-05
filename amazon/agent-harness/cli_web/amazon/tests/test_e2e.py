"""E2E and subprocess tests for cli-web-amazon."""
import json
import os
import shutil
import subprocess
import sys
import unittest

import pytest


# ---------------------------------------------------------------------------
# _resolve_cli helper
# ---------------------------------------------------------------------------

def _resolve_cli(name: str):
    """Resolve installed CLI command; falls back to python -m for dev."""
    force = os.environ.get("CLI_WEB_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-web-", "cli_web.") + "." + name.split("-")[-1] + "_cli"
    return [sys.executable, "-m", module]


CLI = _resolve_cli("cli-web-amazon")


# ---------------------------------------------------------------------------
# Live E2E — public commands (no auth required)
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestE2ESuggest:
    """cli-web-amazon suggest — live autocomplete API."""

    def test_suggest_returns_results(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            suggestions = client.get_suggestions("laptop")
        assert len(suggestions) > 0, "Suggest returned empty list for 'laptop'"
        assert suggestions[0].value, "First suggestion has no value"
        assert suggestions[0].type, "First suggestion has no type"

    def test_suggest_keyword_type(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            suggestions = client.get_suggestions("headphones")
        types = {s.type for s in suggestions}
        assert "KEYWORD" in types, f"Expected KEYWORD type in suggestions; got: {types}"

    def test_suggest_no_rpc_leakage(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            suggestions = client.get_suggestions("phone")
        for s in suggestions:
            assert "wrb.fr" not in s.value, "Raw RPC data leaked into suggestion"
            assert "af.httprm" not in s.value, "Raw RPC data leaked into suggestion"

    def test_suggest_unusual_query_returns_list(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            suggestions = client.get_suggestions("xyzzy12345noresults")
        # May return empty list — just must not raise
        assert isinstance(suggestions, list)


@pytest.mark.e2e
class TestE2ESearch:
    """cli-web-amazon search — live HTML search."""

    def test_search_returns_asins(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            results = client.search("laptop")
        assert len(results) > 0, "Search returned no results for 'laptop'"
        for r in results:
            assert len(r.asin) == 10, f"ASIN {r.asin!r} does not look like a valid ASIN"

    def test_search_result_fields(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            results = client.search("laptop")
        first = results[0]
        assert first.title, "First search result has no title"
        assert first.url.startswith("https://www.amazon.com"), f"URL looks wrong: {first.url}"

    def test_search_url_uses_asin(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            results = client.search("laptop")
        first = results[0]
        assert first.asin in first.url, "ASIN not present in product URL"

    def test_search_pagination(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            page1 = client.search("laptop", page=1)
            page2 = client.search("laptop", page=2)
        # Both pages should have results; they should not be identical
        assert len(page1) > 0
        assert len(page2) > 0
        asin1 = {r.asin for r in page1}
        asin2 = {r.asin for r in page2}
        assert asin1 != asin2, "Page 1 and page 2 returned identical ASINs"

    def test_search_no_rpc_leakage(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            results = client.search("laptop")
        for r in results:
            assert "wrb.fr" not in r.title, "Raw RPC data in search title"


@pytest.mark.e2e
class TestE2EProduct:
    """cli-web-amazon product get — live product detail page."""

    KNOWN_ASIN = "B0GRZ78683"  # Dell Inspiron 15 (stable listing)

    def test_get_product_returns_data(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            product = client.get_product(self.KNOWN_ASIN)
        assert product.asin == self.KNOWN_ASIN
        assert product.title, "Product title is empty"
        assert len(product.title) > 10, "Product title suspiciously short"

    def test_get_product_url_is_dp_url(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            product = client.get_product(self.KNOWN_ASIN)
        assert self.KNOWN_ASIN in product.url, "ASIN not in product URL"
        assert product.url.startswith("https://www.amazon.com"), "URL doesn't start with amazon.com"

    def test_get_product_rating_format(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            product = client.get_product(self.KNOWN_ASIN)
        if product.rating:
            assert "out of 5" in product.rating, f"Unexpected rating format: {product.rating}"

    def test_search_then_get_round_trip(self):
        """Search → pick first ASIN → get product → verify title matches."""
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            results = client.search("laptop")
            assert len(results) > 0
            asin = results[0].asin
            product = client.get_product(asin)
        assert product.asin == asin, "Product ASIN mismatch"
        assert product.title, "Product returned by get has no title"

    def test_get_product_no_rpc_leakage(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            product = client.get_product(self.KNOWN_ASIN)
        assert "wrb.fr" not in product.title, "Raw RPC data in product title"
        assert "af.httprm" not in (product.title + str(product.price)), "Raw RPC data in product"


@pytest.mark.e2e
class TestE2EBestSellers:
    """cli-web-amazon bestsellers — live bestseller page."""

    def test_bestsellers_electronics(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            items = client.get_bestsellers("electronics")
        assert len(items) > 0, "Bestsellers returned no items for electronics"
        assert items[0].rank == 1, f"First item rank should be 1, got {items[0].rank}"

    def test_bestsellers_asin_length(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            items = client.get_bestsellers("electronics")
        for item in items:
            assert len(item.asin) == 10, f"ASIN {item.asin!r} not 10 chars"

    def test_bestsellers_rank_sequential(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            items = client.get_bestsellers("electronics")
        ranks = [i.rank for i in items]
        assert ranks == sorted(ranks), "Ranks are not in ascending order"
        assert ranks[0] == 1, "First rank is not 1"

    def test_bestsellers_title_not_empty(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            items = client.get_bestsellers("books")
        for item in items:
            assert item.title, f"Item with ASIN {item.asin} has empty title"

    def test_bestsellers_url_contains_asin(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            items = client.get_bestsellers("electronics")
        for item in items:
            assert item.asin in item.url, f"ASIN {item.asin} not in URL {item.url}"


# ---------------------------------------------------------------------------
# Subprocess tests — full CLI invocations
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestCLISubprocess:
    """End-to-end subprocess tests using the installed cli-web-amazon binary."""

    def _run(self, args, check=False):
        return subprocess.run(
            CLI + args,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=check,
        )

    def test_help_loads(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "cli-web-amazon" in result.stdout.lower() or "amazon" in result.stdout.lower()

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0

    def test_search_json_output(self):
        result = self._run(["search", "laptop", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list), "Expected JSON array"
        assert len(data) > 0, "Search returned empty list"
        first = data[0]
        assert "asin" in first
        assert "title" in first
        assert len(first["asin"]) == 10, "ASIN not 10 chars"

    def test_search_no_rpc_leak(self):
        result = self._run(["search", "laptop", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        for item in data:
            assert "wrb.fr" not in item.get("title", ""), "Raw RPC data in title"
            assert "af.httprm" not in item.get("title", ""), "Raw RPC data in title"

    def test_suggest_json_output(self):
        result = self._run(["suggest", "laptop", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert "value" in data[0]
        assert "type" in data[0]

    def test_product_get_json_output(self):
        result = self._run(["product", "get", "B0GRZ78683", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert data["asin"] == "B0GRZ78683"
        assert data["title"], "Product title is empty"
        assert "url" in data
        assert "B0GRZ78683" in data["url"]

    def test_product_get_no_rpc_leak(self):
        result = self._run(["product", "get", "B0GRZ78683", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "wrb.fr" not in data.get("title", ""), "Raw RPC data in product title"

    def test_bestsellers_json_output(self):
        result = self._run(["bestsellers", "electronics", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["rank"] == 1

    def test_bestsellers_required_fields(self):
        result = self._run(["bestsellers", "electronics", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        for item in data:
            assert "asin" in item
            assert "title" in item
            assert "rank" in item

    def test_search_with_page(self):
        result = self._run(["search", "laptop", "--page", "2", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_search_with_dept(self):
        result = self._run(["search", "laptop", "--dept", "electronics", "--json"])
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_product_get_unknown_asin_error(self):
        """Unknown ASIN should return a structured error, not a crash."""
        result = self._run(["product", "get", "BADASIN000", "--json"])
        # May return error or empty product — should not crash
        if result.returncode != 0:
            try:
                data = json.loads(result.stdout)
                assert "error" in data
            except json.JSONDecodeError:
                pytest.fail("CLI crashed with non-JSON output on unknown ASIN")

    def test_search_help_subcommand(self):
        result = self._run(["search", "--help"])
        assert result.returncode == 0
        assert "search" in result.stdout.lower()

    def test_product_help_subcommand(self):
        result = self._run(["product", "--help"])
        assert result.returncode == 0

    def test_bestsellers_help_subcommand(self):
        result = self._run(["bestsellers", "--help"])
        assert result.returncode == 0

    def test_suggest_help_subcommand(self):
        result = self._run(["suggest", "--help"])
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
