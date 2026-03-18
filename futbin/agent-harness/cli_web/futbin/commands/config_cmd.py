"""Config commands: set, get, show, reset persistent CLI settings."""
import click
from ..utils.output import print_json
from ..utils.helpers import (
    handle_errors, get_config_value, set_config_value,
    clear_config, get_all_config,
)

VALID_KEYS = {"year", "platform"}


@click.group("config")
def config():
    """Manage persistent CLI settings (year, platform)."""
    pass


@config.command("set")
@click.argument("key", type=click.Choice(sorted(VALID_KEYS)))
@click.argument("value")
def config_set(key, value):
    """Set a config value (e.g., config set year 25)."""
    with handle_errors():
        if key == "year":
            value = int(value)
            if not (22 <= value <= 27):
                raise click.BadParameter(f"Year must be 22-27, got {value}")
        elif key == "platform":
            if value not in ("ps", "pc"):
                raise click.BadParameter(f"Platform must be 'ps' or 'pc', got {value}")
        set_config_value(key, value)
        click.echo(f"Set {key} = {value}")


@config.command("get")
@click.argument("key")
@click.option("--json", "use_json", is_flag=True, default=False)
def config_get(key, use_json):
    """Get a config value."""
    with handle_errors(json_mode=use_json):
        val = get_config_value(key)
        if use_json:
            print_json({key: val})
        else:
            if val is not None:
                click.echo(f"{key} = {val}")
            else:
                click.echo(f"{key} is not set")


@config.command("show")
@click.option("--json", "use_json", is_flag=True, default=False)
def config_show(use_json):
    """Show all config values."""
    with handle_errors(json_mode=use_json):
        cfg = get_all_config()
        # Add defaults for display
        display = {
            "year": cfg.get("year", 26),
            "platform": cfg.get("platform", "ps"),
        }
        if use_json:
            print_json(display)
        else:
            for k, v in display.items():
                default = " (default)" if k not in cfg else ""
                click.echo(f"  {k} = {v}{default}")


@config.command("reset")
def config_reset():
    """Reset all config to defaults."""
    with handle_errors():
        clear_config()
        click.echo("Config reset to defaults (year=26, platform=ps)")
