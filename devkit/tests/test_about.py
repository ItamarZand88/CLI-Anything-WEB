import json

from cli_web_devkit.about import desired_description, fleet_count


def test_desired_description_replaces_count():
    desc = "Claude Code plugin that generates CLIs for any web app. 17 CLIs and counting."
    assert (
        desired_description(desc, 19)
        == "Claude Code plugin that generates CLIs for any web app. 19 CLIs and counting."
    )


def test_desired_description_is_idempotent():
    desc = "Generates CLIs. 19 CLIs and counting."
    assert desired_description(desc, 19) == desc


def test_desired_description_preserves_reworded_prose():
    # Only the count is templated — a hand-edited tagline survives.
    desc = "A totally different tagline — 3 CLIs and counting, more soon!"
    assert (
        desired_description(desc, 19)
        == "A totally different tagline — 19 CLIs and counting, more soon!"
    )


def test_desired_description_appends_when_no_count():
    desc = "Claude Code plugin that generates CLIs for any web app."
    assert desired_description(desc, 19) == (
        "Claude Code plugin that generates CLIs for any web app. 19 CLIs and counting."
    )


def test_desired_description_only_replaces_first_count():
    desc = "5 CLIs now, was 2 CLIs before."
    assert desired_description(desc, 19) == "19 CLIs now, was 2 CLIs before."


def test_fleet_count_matches_registry(tmp_path):
    registry = {
        "version": "1.0.0",
        "clis": [
            {
                "name": f"cli-web-app{i}",
                "website": "example.com",
                "protocol": "REST",
                "auth": "none",
                "directory": f"app{i}/agent-harness",
                "namespace": f"cli_web.app{i}",
                "commands": ["things list"],
                "install": f"pip install -e app{i}/agent-harness",
            }
            for i in range(7)
        ],
    }
    (tmp_path / "registry.json").write_text(json.dumps(registry))
    assert fleet_count(tmp_path) == 7
