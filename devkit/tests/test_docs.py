import json

from cli_web_devkit.docs import generate, render_install, render_site_data, render_table
from cli_web_devkit.paths import repo_root
from cli_web_devkit.registry import Registry

ROOT = repo_root()
REGISTRY = Registry.load(ROOT / "registry.json")


def test_table_has_one_row_per_cli():
    table = render_table(REGISTRY)
    rows = [line for line in table.splitlines() if line.startswith("| [`cli-web-")]
    assert len(rows) == len(REGISTRY.clis)


def test_table_auth_display_is_human():
    table = render_table(REGISTRY)
    assert "Google SSO" in table
    assert "Google_sso" not in table


def test_install_block_covers_whole_fleet():
    block = render_install(REGISTRY)
    # Whole-fleet coverage now comes from the umbrella package, not an
    # exhaustive per-directory list.
    assert "pip install cli-anything-web" in block
    # ...and at least one real CLI is shown as the single-package example.
    assert any(entry.name in block for entry in REGISTRY.clis), "no CLI name in install block"
    assert "```bash" in block


def test_site_data_has_one_public_install_per_cli():
    data = render_site_data(REGISTRY)
    cards = json.loads(data.removeprefix("const data = ").removesuffix(";"))
    assert len(cards) == len(REGISTRY.clis)
    cards_by_name = {card["name"]: card for card in cards}
    for entry in REGISTRY.clis:
        card = cards_by_name[entry.app_dir]
        assert card["install"] == entry.install
        assert card["setup"] == entry.extra.get("post_install", [])
        assert card["cmds"] == entry.commands


def test_public_docs_are_fresh():
    """README and registry site must match registry (run `cli-web-devkit docs`)."""
    assert generate(ROOT, check=True), "README.md or registry site generated data is stale"
