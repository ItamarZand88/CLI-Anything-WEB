from cli_web_core.repl_skin import _ACCENT_COLORS, SKIN_VERSION, ReplSkin


def _skin(**kwargs) -> ReplSkin:
    kwargs.setdefault("history_file", "/tmp/cli-web-core-test-history")
    return ReplSkin("demo_app", **kwargs)


def test_skin_version_marker():
    assert SKIN_VERSION == "2.0.0"


def test_default_display_name_and_accent():
    skin = _skin()
    assert skin.display_name == "Demo App"
    assert skin.app == "demo_app"


def test_display_name_override():
    skin = _skin(display_name="DEMO!")
    assert skin.display_name == "DEMO!"


def test_accent_override_beats_table():
    skin = ReplSkin("amazon", accent="\033[38;5;99m", history_file="/tmp/h")
    assert skin.accent == "\033[38;5;99m"


def test_fleet_apps_have_brand_accents():
    for app in ("amazon", "airbnb", "linkedin", "hackernews", "youtube"):
        assert app in _ACCENT_COLORS


def test_banner_and_messages_do_not_crash(capsys):
    skin = _skin()
    skin.print_banner()
    skin.success("ok")
    skin.error("bad")
    skin.warning("careful")
    skin.info("fyi")
    out = capsys.readouterr()
    assert "Demo App" in out.out
    assert "bad" in out.err


def test_no_color_env_disables_ansi(monkeypatch, capsys):
    monkeypatch.setenv("NO_COLOR", "1")
    skin = _skin()
    skin.success("plain")
    out = capsys.readouterr().out
    assert "\033[" not in out


def test_prompt_toolkit_failure_degrades_gracefully(monkeypatch):
    """Any prompt_toolkit failure must yield the plain-input fallback."""
    import builtins

    real_import = builtins.__import__

    def broken_import(name, *args, **kwargs):
        if name.startswith("prompt_toolkit"):
            raise RuntimeError("simulated broken prompt_toolkit")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)
    skin = _skin()
    assert skin.create_prompt_session() is None
    assert skin.get_prompt_style() is None
