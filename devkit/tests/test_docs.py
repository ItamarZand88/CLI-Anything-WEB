from cli_web_devkit.docs import generate, render_install, render_table
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
    for entry in REGISTRY.clis:
        assert entry.directory in block, f"{entry.name} missing from install block"
    assert block.startswith("```bash") and block.endswith("```")


def test_real_readme_is_fresh():
    """README fleet sections must match registry (run `cli-web-devkit docs`)."""
    assert generate(ROOT, check=True), "README.md fleet sections are stale"
