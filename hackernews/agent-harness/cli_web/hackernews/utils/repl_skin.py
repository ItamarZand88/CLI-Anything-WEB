"""cli-web REPL Skin — Unified terminal interface for all cli-web-* CLIs.

Copy this file into your CLI package at:
    cli_web/<app>/utils/repl_skin.py

Usage:
    from cli_web.<app>.utils.repl_skin import ReplSkin

    skin = ReplSkin("monday", version="1.0.0")
    skin.print_banner()
    prompt_text = skin.prompt(context="Board: Sprint 42")
    skin.success("Items created")
    skin.error("Auth token expired")
    skin.warning("Rate limit approaching")
    skin.info("Fetching 24 items...")
    skin.status("Workspace", "my-team")
    skin.table(headers, rows)
    skin.print_goodbye()
"""

import os
import sys

# ── ANSI color codes (no external deps for core styling) ──────────────

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_ITALIC = "\033[3m"
_UNDERLINE = "\033[4m"

# Brand colors
_CYAN = "\033[38;5;80m"       # cli-web brand cyan
_CYAN_BG = "\033[48;5;80m"
_WHITE = "\033[97m"
_GRAY = "\033[38;5;245m"
_DARK_GRAY = "\033[38;5;240m"
_LIGHT_GRAY = "\033[38;5;250m"

# Web app accent colors — each app gets a unique accent
_ACCENT_COLORS = {
    "monday":    "\033[38;5;214m",   # warm orange (Monday.com brand)
    "notion":    "\033[38;5;255m",   # near-white (Notion brand)
    "linear":    "\033[38;5;99m",    # purple (Linear brand)
    "jira":      "\033[38;5;27m",    # blue (Jira brand)
    "slack":     "\033[38;5;55m",    # aubergine (Slack brand)
    "github":    "\033[38;5;240m",   # dark gray (GitHub brand)
    "figma":     "\033[38;5;213m",   # pink (Figma brand)
    "airtable":  "\033[38;5;35m",    # green (Airtable brand)
    "asana":     "\033[38;5;196m",   # red (Asana brand)
    "trello":    "\033[38;5;39m",    # blue (Trello brand)
}
_DEFAULT_ACCENT = "\033[38;5;75m"      # default sky blue

# Status colors
_GREEN = "\033[38;5;78m"
_YELLOW = "\033[38;5;220m"
_RED = "\033[38;5;196m"
_BLUE = "\033[38;5;75m"
_MAGENTA = "\033[38;5;176m"

# ── Brand icon ────────────────────────────────────────────────────────

_ICON = f"{_CYAN}{_BOLD}◆{_RESET}"
_ICON_SMALL = f"{_CYAN}▸{_RESET}"

# ── Box drawing characters ────────────────────────────────────────────

_H_LINE = "─"
_V_LINE = "│"
_TL = "╭"
_TR = "╮"
_BL = "╰"
_BR = "╯"
_T_DOWN = "┬"
_T_UP = "┴"
_T_RIGHT = "├"
_T_LEFT = "┤"
_CROSS = "┼"


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes for length calculation."""
    import re
    return re.sub(r"\033\[[^m]*m", "", text)


def _visible_len(text: str) -> int:
    """Get visible length of text (excluding ANSI codes)."""
    return len(_strip_ansi(text))


class ReplSkin:
    """Unified REPL skin for cli-web-* CLIs.

    Provides consistent branding, prompts, and message formatting
    across all CLI harnesses built with the cli-anything-web methodology.
    """

    def __init__(self, app: str, version: str = "1.0.0",
                 history_file: str | None = None,
                 display_name: str | None = None):
        """Initialize the REPL skin.

        Args:
            app: App name (e.g., "monday", "notion", "jira").
            version: CLI version string.
            history_file: Path for persistent command history.
                         Defaults to ~/.cli-web-<app>/history
            display_name: Override for the banner display name.
        """
        self.app = app.lower().replace("-", "_")
        self.display_name = display_name or app.replace("_", " ").title()
        self.version = version
        self.accent = _ACCENT_COLORS.get(self.app, _DEFAULT_ACCENT)

        # History file
        if history_file is None:
            from pathlib import Path
            hist_dir = Path.home() / f".cli-web-{self.app}"
            hist_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = str(hist_dir / "history")
        else:
            self.history_file = history_file

        # Detect terminal capabilities
        self._color = self._detect_color_support()

    def _detect_color_support(self) -> bool:
        """Check if terminal supports color."""
        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("CLI_WEB_NO_COLOR"):
            return False
        if not hasattr(sys.stdout, "isatty"):
            return False
        return sys.stdout.isatty()

    def _c(self, code: str, text: str) -> str:
        """Apply color code if colors are supported."""
        if not self._color:
            return text
        return f"{code}{text}{_RESET}"

    # ── Banner ────────────────────────────────────────────────────────

    def print_banner(self):
        """Print the startup banner with branding."""
        inner = 54

        def _box_line(content: str) -> str:
            """Wrap content in box drawing, padding to inner width."""
            pad = inner - _visible_len(content)
            vl = self._c(_DARK_GRAY, _V_LINE)
            return f"{vl}{content}{' ' * max(0, pad)}{vl}"

        top = self._c(_DARK_GRAY, f"{_TL}{_H_LINE * inner}{_TR}")
        bot = self._c(_DARK_GRAY, f"{_BL}{_H_LINE * inner}{_BR}")

        # Title:  ◆  cli-web · Monday
        icon = self._c(_CYAN + _BOLD, "◆")
        brand = self._c(_CYAN + _BOLD, "cli-web")
        dot = self._c(_DARK_GRAY, "·")
        name = self._c(self.accent + _BOLD, self.display_name)
        title = f" {icon}  {brand} {dot} {name}"

        ver = f" {self._c(_DARK_GRAY, f'   v{self.version}')}"
        tip = f" {self._c(_DARK_GRAY, '   Type help for commands, quit to exit')}"
        empty = ""

        print(top)
        print(_box_line(title))
        print(_box_line(ver))
        print(_box_line(empty))
        print(_box_line(tip))
        print(bot)
        print()

    # ── Prompt ────────────────────────────────────────────────────────

    def prompt(self, project_name: str = "", modified: bool = False,
               context: str = "") -> str:
        """Build a styled prompt string for prompt_toolkit or input()."""
        parts = []

        if self._color:
            parts.append(f"{_CYAN}◆{_RESET} ")
        else:
            parts.append("> ")

        parts.append(self._c(self.accent + _BOLD, self.app))

        if project_name or context:
            ctx = context or project_name
            mod = "*" if modified else ""
            parts.append(f" {self._c(_DARK_GRAY, '[')}")
            parts.append(self._c(_LIGHT_GRAY, f"{ctx}{mod}"))
            parts.append(self._c(_DARK_GRAY, ']'))

        parts.append(self._c(_GRAY, " ❯ "))

        return "".join(parts)

    def prompt_tokens(self, project_name: str = "", modified: bool = False,
                      context: str = ""):
        """Build prompt_toolkit formatted text tokens for the prompt."""
        tokens = []

        tokens.append(("class:icon", "◆ "))
        tokens.append(("class:app", self.app))

        if project_name or context:
            ctx = context or project_name
            mod = "*" if modified else ""
            tokens.append(("class:bracket", " ["))
            tokens.append(("class:context", f"{ctx}{mod}"))
            tokens.append(("class:bracket", "]"))

        tokens.append(("class:arrow", " ❯ "))

        return tokens

    def get_prompt_style(self):
        """Get a prompt_toolkit Style object matching the skin."""
        try:
            from prompt_toolkit.styles import Style
        except ImportError:
            return None

        accent_hex = _ANSI_256_TO_HEX.get(self.accent, "#5fafff")

        return Style.from_dict({
            "icon": "#5fdfdf bold",
            "app": f"{accent_hex} bold",
            "bracket": "#585858",
            "context": "#bcbcbc",
            "arrow": "#808080",
            "completion-menu.completion": "bg:#303030 #bcbcbc",
            "completion-menu.completion.current": f"bg:{accent_hex} #000000",
            "completion-menu.meta.completion": "bg:#303030 #808080",
            "completion-menu.meta.completion.current": f"bg:{accent_hex} #000000",
            "auto-suggest": "#585858",
            "bottom-toolbar": "bg:#1c1c1c #808080",
            "bottom-toolbar.text": "#808080",
        })

    # ── Messages ──────────────────────────────────────────────────────

    def success(self, message: str):
        """Print a success message with green checkmark."""
        icon = self._c(_GREEN + _BOLD, "✓")
        print(f"  {icon} {self._c(_GREEN, message)}")

    def error(self, message: str):
        """Print an error message with red cross."""
        icon = self._c(_RED + _BOLD, "✗")
        print(f"  {icon} {self._c(_RED, message)}", file=sys.stderr)

    def warning(self, message: str):
        """Print a warning message with yellow triangle."""
        icon = self._c(_YELLOW + _BOLD, "⚠")
        print(f"  {icon} {self._c(_YELLOW, message)}")

    def info(self, message: str):
        """Print an info message with blue dot."""
        icon = self._c(_BLUE, "●")
        print(f"  {icon} {self._c(_LIGHT_GRAY, message)}")

    def hint(self, message: str):
        """Print a subtle hint message."""
        print(f"  {self._c(_DARK_GRAY, message)}")

    def section(self, title: str):
        """Print a section header."""
        print()
        print(f"  {self._c(self.accent + _BOLD, title)}")
        print(f"  {self._c(_DARK_GRAY, _H_LINE * len(title))}")

    # ── Status display ────────────────────────────────────────────────

    def status(self, label: str, value: str):
        """Print a key-value status line."""
        lbl = self._c(_GRAY, f"  {label}:")
        val = self._c(_WHITE, f" {value}")
        print(f"{lbl}{val}")

    def status_block(self, items: dict[str, str], title: str = ""):
        """Print a block of status key-value pairs."""
        if title:
            self.section(title)

        max_key = max(len(k) for k in items) if items else 0
        for label, value in items.items():
            lbl = self._c(_GRAY, f"  {label:<{max_key}}")
            val = self._c(_WHITE, f"  {value}")
            print(f"{lbl}{val}")

    def progress(self, current: int, total: int, label: str = ""):
        """Print a simple progress indicator."""
        pct = int(current / total * 100) if total > 0 else 0
        bar_width = 20
        filled = int(bar_width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)
        text = f"  {self._c(_CYAN, bar)} {self._c(_GRAY, f'{pct:3d}%')}"
        if label:
            text += f" {self._c(_LIGHT_GRAY, label)}"
        print(text)

    # ── Table display ─────────────────────────────────────────────────

    def table(self, headers: list[str], rows: list[list[str]],
              max_col_width: int = 40):
        """Print a formatted table with box-drawing characters."""
        if not headers:
            return

        col_widths = [min(len(h), max_col_width) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = min(
                        max(col_widths[i], len(str(cell))), max_col_width
                    )

        def pad(text: str, width: int) -> str:
            t = str(text)[:width]
            return t + " " * (width - len(t))

        header_cells = [
            self._c(_CYAN + _BOLD, pad(h, col_widths[i]))
            for i, h in enumerate(headers)
        ]
        sep = self._c(_DARK_GRAY, f" {_V_LINE} ")
        print(f"  {sep.join(header_cells)}")

        sep_line = self._c(
            _DARK_GRAY,
            f"  {'───'.join([_H_LINE * w for w in col_widths])}"
        )
        print(sep_line)

        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    cells.append(
                        self._c(_LIGHT_GRAY, pad(str(cell), col_widths[i]))
                    )
            row_sep = self._c(_DARK_GRAY, f" {_V_LINE} ")
            print(f"  {row_sep.join(cells)}")

    # ── Help display ──────────────────────────────────────────────────

    def help(self, commands: dict[str, str]):
        """Print a formatted help listing."""
        self.section("Commands")
        max_cmd = max(len(c) for c in commands) if commands else 0
        for cmd, desc in commands.items():
            cmd_styled = self._c(self.accent, f"  {cmd:<{max_cmd}}")
            desc_styled = self._c(_GRAY, f"  {desc}")
            print(f"{cmd_styled}{desc_styled}")
        print()

    # ── Goodbye ───────────────────────────────────────────────────────

    def print_goodbye(self):
        """Print a styled goodbye message."""
        print(f"\n  {_ICON_SMALL} {self._c(_GRAY, 'Goodbye!')}\n")

    # ── Prompt toolkit session factory ────────────────────────────────

    def create_prompt_session(self):
        """Create a prompt_toolkit PromptSession with skin styling."""
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

            style = self.get_prompt_style()

            session = PromptSession(
                history=FileHistory(self.history_file),
                auto_suggest=AutoSuggestFromHistory(),
                style=style,
                enable_history_search=True,
            )
            return session
        except ImportError:
            return None

    def get_input(self, pt_session, project_name: str = "",
                  modified: bool = False, context: str = "") -> str:
        """Get input from user using prompt_toolkit or fallback."""
        if pt_session is not None:
            from prompt_toolkit.formatted_text import FormattedText
            tokens = self.prompt_tokens(project_name, modified, context)
            return pt_session.prompt(FormattedText(tokens)).strip()
        else:
            raw_prompt = self.prompt(project_name, modified, context)
            return input(raw_prompt).strip()

    # ── Toolbar builder ───────────────────────────────────────────────

    def bottom_toolbar(self, items: dict[str, str]):
        """Create a bottom toolbar callback for prompt_toolkit."""
        def toolbar():
            from prompt_toolkit.formatted_text import FormattedText
            parts = []
            for i, (k, v) in enumerate(items.items()):
                if i > 0:
                    parts.append(("class:bottom-toolbar.text", "  │  "))
                parts.append(("class:bottom-toolbar.text", f" {k}: "))
                parts.append(("class:bottom-toolbar", v))
            return FormattedText(parts)
        return toolbar


# ── ANSI 256-color to hex mapping (for prompt_toolkit styles) ─────────

_ANSI_256_TO_HEX = {
    # Base entries (from reference implementation)
    "\033[38;5;33m":  "#0087ff",
    "\033[38;5;35m":  "#00af5f",
    "\033[38;5;39m":  "#00afff",
    "\033[38;5;40m":  "#00d700",
    "\033[38;5;55m":  "#5f00af",
    "\033[38;5;69m":  "#5f87ff",
    "\033[38;5;75m":  "#5fafff",
    "\033[38;5;80m":  "#5fd7d7",
    "\033[38;5;208m": "#ff8700",
    "\033[38;5;214m": "#ffaf00",
    # Web app accent colors
    "\033[38;5;255m": "#eeeeee",  # notion
    "\033[38;5;99m":  "#875fff",  # linear
    "\033[38;5;27m":  "#005fff",  # jira
    "\033[38;5;240m": "#585858",  # github
    "\033[38;5;213m": "#ff87ff",  # figma
    "\033[38;5;196m": "#ff0000",  # asana
}
