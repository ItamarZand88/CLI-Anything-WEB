"""Output formatting for cli-web-gai."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ..core.models import SearchResult

console = Console()


def print_search_result(result: SearchResult):
    """Print a search result in human-readable format."""

    console.print()
    console.print(
        Panel(
            Text(result.query, style="bold cyan"),
            title="[bold]Google AI Mode[/bold]",
            border_style="blue",
        )
    )

    console.print()

    # Answer body as Markdown
    console.print(Markdown(result.answer))
    console.print()

    # Sources list
    if result.sources:
        console.print(f"[bold]Sources ({len(result.sources)}):[/bold]")
        for i, src in enumerate(result.sources, 1):
            console.print(f"  [{i}] [link={src.url}]{src.title}[/link]")
            if not src.snippet:
                continue
            console.print(f"      [dim]{src.snippet[:100]}[/dim]")
        console.print()

    # Follow-up prompt
    if result.follow_up_prompt:
        console.print(f"[dim italic]{result.follow_up_prompt}[/dim italic]")
        console.print()
