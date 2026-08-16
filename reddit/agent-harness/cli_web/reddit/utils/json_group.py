"""Click group that preserves structured errors before command callbacks run."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from typing import Any

import click


class JsonGroup(click.Group):
    """Render Click usage errors as JSON when ``--json`` was requested."""

    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        if not standalone_mode:
            return super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )

        actual_args = list(args) if args is not None else sys.argv[1:]
        try:
            return super().main(
                args=actual_args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )
        except click.UsageError as exc:
            if "--json" in actual_args:
                click.echo(
                    json.dumps(
                        {"error": True, "code": "USAGE_ERROR", "message": exc.format_message()}
                    )
                )
            else:
                exc.show()
            raise SystemExit(exc.exit_code) from exc
        except click.exceptions.Exit as exc:
            raise SystemExit(exc.exit_code) from exc
        except click.Abort as exc:
            if "--json" in actual_args:
                click.echo(json.dumps({"error": True, "code": "ABORTED", "message": "Aborted"}))
            else:
                click.echo("Aborted!", err=True)
            raise SystemExit(1) from exc
