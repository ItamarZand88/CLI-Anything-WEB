"""Unit tests for cli-web-amazon core modules (mocked HTTP)."""
import json
import unittest
from unittest.mock import patch, MagicMock

from cli_web.amazon.core.exceptions import (
    AmazonError, NetworkError, NotFoundError,
    ParsingError, RateLimitError, ServerError, error_code_for,
)
from cli_web.amazon.core.models import (
    SearchResult, Product, BestSeller, Suggestion,
)
from cli_web.amazon.utils.helpers import handle_errors, sanitize_filename


# ---------------------------------------------------------------------------
# Exception hierarchy tests
# ---------------------------------------------------------------------------

class TestExceptions(unittest.TestCase):

    def test_rate_limit_error_with_retry_after(self):
        exc = RateLimitError("too many requests", retry_after=60.0)
        self.assertEqual(exc.retry_after, 60.0)

    def test_server_error_status_code(self):
        exc = ServerError("internal error", status_code=503)
        self.assertEqual(exc.status_code, 503)

    def test_error_code_for_rate_limit(self):
        self.assertEqual(error_code_for(RateLimitError("x")), "RATE_LIMITED")

    def test_error_code_for_not_found(self):
        self.assertEqual(error_code_for(NotFoundError("x")), "NOT_FOUND")

    def test_error_code_for_server_error(self):
        self.assertEqual(error_code_for(ServerError("x")), "SERVER_ERROR")

    def test_error_code_for_unknown(self):
        self.assertEqual(error_code_for(ValueError("x")), "UNKNOWN_ERROR")


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestModels(unittest.TestCase):

    def test_search_result_to_dict(self):
        r = SearchResult(
            asin="B0GRZ78683",
            title="Dell Laptop",
            price="$799",
            rating="4.8 out of 5 stars",
            review_count="(14)",
            url="https://www.amazon.com/dp/B0GRZ78683",
        )
        d = r.to_dict()
        self.assertEqual(d["asin"], "B0GRZ78683")
        self.assertEqual(d["title"], "Dell Laptop")
        self.assertIn("price", d)
        self.assertIn("rating", d)

    def test_product_to_dict(self):
        p = Product(
            asin="B0GRZ78683",
            title="Dell Laptop",
            price="$799",
            brand="Dell",
        )
        d = p.to_dict()
        self.assertEqual(d["asin"], "B0GRZ78683")
        self.assertEqual(d["brand"], "Dell")

    def test_bestseller_to_dict(self):
        b = BestSeller(rank=1, asin="B08JHCVHTY", title="Blink Camera", price="$34.99")
        d = b.to_dict()
        self.assertEqual(d["rank"], 1)
        self.assertEqual(d["asin"], "B08JHCVHTY")

    def test_suggestion_to_dict(self):
        s = Suggestion(value="laptop stand", type="KEYWORD")
        d = s.to_dict()
        self.assertEqual(d["value"], "laptop stand")
        self.assertEqual(d["type"], "KEYWORD")



# ---------------------------------------------------------------------------
# Client tests (mocked)
# ---------------------------------------------------------------------------

class TestClientSuggestions(unittest.TestCase):
    """Test suggestions API with mocked httpx."""

    def _mock_response(self, json_data: dict, status: int = 200):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data
        resp.text = json.dumps(json_data)
        return resp

    def test_get_suggestions_parses_keywords(self):
        from cli_web.amazon.core.client import AmazonClient
        suggestions_json = {
            "suggestions": [
                {"value": "laptop", "type": "KEYWORD"},
                {"value": "laptop stand", "type": "KEYWORD"},
            ]
        }
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_response(suggestions_json)):
                results = client.get_suggestions("laptop")

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].value, "laptop")
        self.assertEqual(results[1].value, "laptop stand")

    def test_get_suggestions_empty_results(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_response({"suggestions": []})):
                results = client.get_suggestions("zzzzzzz")
        self.assertEqual(results, [])

    def test_get_suggestions_429_raises_rate_limit(self):
        from cli_web.amazon.core.client import AmazonClient
        resp = MagicMock()
        resp.status_code = 429
        resp.headers = {"retry-after": "30"}
        with AmazonClient() as client:
            with patch.object(client._client, "get", return_value=resp):
                with self.assertRaises(RateLimitError) as ctx:
                    client.get_suggestions("test")
        self.assertEqual(ctx.exception.retry_after, 30.0)


class TestClientSearch(unittest.TestCase):
    """Test search parsing with mocked HTML."""

    SEARCH_HTML = """
    <html><body>
    <div data-component-type="s-search-result" data-asin="B0GRZ78683">
        <h2>Dell Inspiron 15 Laptop</h2>
        <span class="a-icon-alt">4.8 out of 5 stars</span>
        <span aria-label="14 ratings">14 ratings</span>
        <a class="a-link-normal" href="/dp/B0GRZ78683">View</a>
    </div>
    <div data-component-type="s-search-result" data-asin="B09R6FNNS1">
        <h2>HP Laptop 15</h2>
        <span class="a-icon-alt">4.3 out of 5 stars</span>
        <a class="a-link-normal" href="/dp/B09R6FNNS1">View</a>
    </div>
    </body></html>
    """

    def _mock_html_response(self, html: str):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        return resp

    def test_search_returns_products(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response(self.SEARCH_HTML)):
                results = client.search("laptop")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].asin, "B0GRZ78683")
        self.assertEqual(results[0].title, "Dell Inspiron 15 Laptop")
        self.assertIn("4.8", results[0].rating)

    def test_search_empty_page(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response("<html></html>")):
                results = client.search("xyzabc123")
        self.assertEqual(results, [])

    def test_search_url_normalization(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response(self.SEARCH_HTML)):
                results = client.search("laptop")
        # URL should start with https://www.amazon.com
        self.assertTrue(results[0].url.startswith("https://www.amazon.com"))


class TestClientProductDetail(unittest.TestCase):
    """Test product detail parsing."""

    PRODUCT_HTML = """
    <html><body>
    <span id="productTitle">Dell Inspiron 15 Laptop Computer</span>
    <span class="a-offscreen">$799.90</span>
    <span id="acrPopover" title="4.8 out of 5 stars"></span>
    <span id="acrCustomerReviewText">(14)</span>
    <a id="bylineInfo">Visit the Dell Store</a>
    <img id="landingImage" src="https://m.media-amazon.com/images/I/example.jpg">
    </body></html>
    """

    def _mock_html_response(self, html: str, url: str = "https://www.amazon.com/dp/B0GRZ78683"):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        resp.url = url
        return resp

    def test_get_product_parses_all_fields(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response(self.PRODUCT_HTML)):
                product = client.get_product("B0GRZ78683")

        self.assertEqual(product.asin, "B0GRZ78683")
        self.assertEqual(product.title, "Dell Inspiron 15 Laptop Computer")
        self.assertEqual(product.price, "$799.90")
        self.assertEqual(product.rating, "4.8 out of 5 stars")
        self.assertEqual(product.review_count, "(14)")
        self.assertEqual(product.brand, "Visit the Dell Store")
        self.assertIn("m.media-amazon.com", product.image_url)

    def test_get_product_url(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response(self.PRODUCT_HTML)):
                product = client.get_product("B0GRZ78683")
        self.assertEqual(product.url, "https://www.amazon.com/dp/B0GRZ78683")


class TestClientBestSellers(unittest.TestCase):
    """Test bestsellers parsing."""

    BESTSELLERS_HTML = """
    <html><body>
    <div id="gridItemRoot">
        <div data-asin="B08JHCVHTY">
            <span class="zg-bdg-text">#1</span>
            <img alt="Blink Outdoor Camera">
            <a class="a-link-normal" href="/dp/B08JHCVHTY">View</a>
            <span class="p13n-sc-price">$34.99</span>
        </div>
    </div>
    <div id="gridItemRoot">
        <div data-asin="B0DCH8VDXF">
            <span class="zg-bdg-text">#2</span>
            <img alt="Apple EarPods">
            <a class="a-link-normal" href="/dp/B0DCH8VDXF">View</a>
            <span class="p13n-sc-price">$19.00</span>
        </div>
    </div>
    </body></html>
    """

    def _mock_html_response(self, html: str):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        return resp

    def test_get_bestsellers_parses_items(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response(self.BESTSELLERS_HTML)):
                items = client.get_bestsellers("electronics")

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].asin, "B08JHCVHTY")
        self.assertEqual(items[0].rank, 1)
        self.assertEqual(items[0].title, "Blink Outdoor Camera")
        self.assertEqual(items[0].price, "$34.99")

    def test_get_bestsellers_rank_order(self):
        from cli_web.amazon.core.client import AmazonClient
        with AmazonClient() as client:
            with patch.object(client._client, "get",
                              return_value=self._mock_html_response(self.BESTSELLERS_HTML)):
                items = client.get_bestsellers("electronics")
        self.assertEqual(items[0].rank, 1)
        self.assertEqual(items[1].rank, 2)


# ---------------------------------------------------------------------------
# Helpers tests
# ---------------------------------------------------------------------------

class TestHelpers(unittest.TestCase):

    def test_sanitize_filename_basic(self):
        self.assertEqual(sanitize_filename("my product"), "my product")

    def test_sanitize_filename_invalid_chars(self):
        result = sanitize_filename("product/name:value")
        self.assertNotIn("/", result)
        self.assertNotIn(":", result)

    def test_sanitize_filename_empty(self):
        self.assertEqual(sanitize_filename(""), "untitled")
        self.assertEqual(sanitize_filename("   "), "untitled")

    def test_handle_errors_not_found_exits_1(self):
        with self.assertRaises(SystemExit) as ctx:
            with handle_errors(json_mode=False):
                raise NotFoundError("item not found")
        self.assertEqual(ctx.exception.code, 1)

    def test_handle_errors_json_mode_outputs_json(self):
        from unittest.mock import patch as mock_patch
        output = []
        with mock_patch("click.echo", side_effect=output.append):
            try:
                with handle_errors(json_mode=True):
                    raise NotFoundError("item not found")
            except SystemExit:
                pass
        self.assertEqual(len(output), 1)
        data = json.loads(output[0])
        self.assertTrue(data["error"])
        self.assertEqual(data["code"], "NOT_FOUND")

    def test_handle_errors_unknown_exits_2(self):
        with self.assertRaises(SystemExit) as ctx:
            with handle_errors(json_mode=False):
                raise ValueError("unexpected bug")
        self.assertEqual(ctx.exception.code, 2)

    def test_handle_errors_keyboard_interrupt_exits_130(self):
        with self.assertRaises(SystemExit) as ctx:
            with handle_errors(json_mode=False):
                raise KeyboardInterrupt()
        self.assertEqual(ctx.exception.code, 130)


if __name__ == "__main__":
    unittest.main()
