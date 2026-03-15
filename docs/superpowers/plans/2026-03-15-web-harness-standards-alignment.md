# Web-Harness Standards Alignment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring cli-anything-web-plugin to production quality — rename WEB-HARNESS.md to CLI-ANYTHING-WEB.md, port the ReplSkin class, fill pipeline gaps (Phase 5 Test Planning, Response Verification), apply standalone framing, and add missing infrastructure.

**Architecture:** Sequential file edits to the plugin at `cli-anything-web-plugin/`. Task 1 (rename) must run first since all other tasks reference the new filename. Task 2 (repl_skin.py) is the only Python code — uses a quick import smoke test. All other tasks are markdown/shell file edits verified by grep.

**Tech Stack:** Python 3.10+ (repl_skin.py with prompt_toolkit), Bash (verify-plugin.sh), Markdown

**Spec:** `docs/superpowers/specs/2026-03-15-web-harness-standards-alignment.md`

**Reference repo:** `C:/Users/ItamarZand/Desktop/02_Projects/Personal/CLI-Anything/cli-anything-plugin/`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `cli-anything-web-plugin/WEB-HARNESS.md` | Rename to `CLI-ANYTHING-WEB.md` | Methodology SOP |
| `cli-anything-web-plugin/CLI-ANYTHING-WEB.md` | Major edit | Standalone framing, Phase 5, Rules, Testing Strategy |
| `cli-anything-web-plugin/scripts/repl_skin.py` | Complete rewrite | Unified REPL skin with prompt_toolkit |
| `cli-anything-web-plugin/commands/validate.md` | Complete rewrite | 8-category N/N validation |
| `cli-anything-web-plugin/commands/web-harness.md` | Edit | Reference update + Success Criteria + Output Structure |
| `cli-anything-web-plugin/commands/record.md` | Edit | Reference update only |
| `cli-anything-web-plugin/commands/refine.md` | Edit | Reference update + gap-present step + Success Criteria |
| `cli-anything-web-plugin/commands/test.md` | Edit | Reference update + subprocess verification + Failure Handling |
| `cli-anything-web-plugin/commands/list.md` | Edit | Reference update only |
| `cli-anything-web-plugin/scripts/setup-web-harness.sh` | Edit | Reference update only |
| `cli-anything-web-plugin/README.md` | Edit | Standalone framing + marketplace removal + list command |
| `cli-anything-web-plugin/QUICKSTART.md` | Verify | Check for stale references (none expected) |
| `cli-anything-web-plugin/skills/web-harness-methodology/SKILL.md` | Edit | Reference update (missed by spec but broken if skipped) |
| `cli-anything-web-plugin/verify-plugin.sh` | Create | Plugin structure checker |
| `cli-anything-web-plugin/LICENSE` | Create | MIT license |

---

## Chunk 1: Foundation (Rename + ReplSkin)

### Task 1: Rename WEB-HARNESS.md → CLI-ANYTHING-WEB.md

**Files:**
- Rename: `cli-anything-web-plugin/WEB-HARNESS.md` → `cli-anything-web-plugin/CLI-ANYTHING-WEB.md`
- Modify: `cli-anything-web-plugin/commands/web-harness.md`
- Modify: `cli-anything-web-plugin/commands/record.md`
- Modify: `cli-anything-web-plugin/commands/refine.md`
- Modify: `cli-anything-web-plugin/commands/test.md`
- Modify: `cli-anything-web-plugin/commands/validate.md`
- Modify: `cli-anything-web-plugin/commands/list.md`
- Modify: `cli-anything-web-plugin/scripts/setup-web-harness.sh`
- Modify: `cli-anything-web-plugin/README.md`
- Modify: `cli-anything-web-plugin/skills/web-harness-methodology/SKILL.md`

- [ ] **Step 1: Rename the file**

```bash
cd cli-anything-web-plugin && mv WEB-HARNESS.md CLI-ANYTHING-WEB.md
```

- [ ] **Step 2: Update the title line in CLI-ANYTHING-WEB.md**

Change line 1 from:
```
# WEB-HARNESS.md — Methodology SOP
```
To:
```
# CLI-ANYTHING-WEB.md — Methodology SOP
```

- [ ] **Step 3: Update all 6 command files — replace `WEB-HARNESS.md` with `CLI-ANYTHING-WEB.md`**

In each of these files, make these replacements (3 occurrences per file):

**`commands/web-harness.md`:**
- Line 8: `## CRITICAL: Read WEB-HARNESS.md First` → `## CRITICAL: Read CLI-ANYTHING-WEB.md First`
- Line 10: `read \`${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md\`` → `read \`${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md\``
- Line 15: `@${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md` → `@${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`

Apply the same 3-replacement pattern to:
- `commands/record.md` (lines 8, 10, 15)
- `commands/refine.md` (lines 8, 10, 15)
- `commands/test.md` (lines 8, 10, 15)
- `commands/validate.md` (lines 3 description, 8, 10, 15)
- `commands/list.md` (lines 8, 10 — only 2 occurrences, no `@` line)

**`commands/validate.md` extra:** Line 3 frontmatter description mentions `WEB-HARNESS.md`:
```
description: Validate a web-harness CLI against WEB-HARNESS.md standards and best practices.
```
→
```
description: Validate a web-harness CLI against CLI-ANYTHING-WEB.md standards and best practices.
```

- [ ] **Step 4: Update setup-web-harness.sh**

Line 121: `echo "  WEB-HARNESS.md: See plugin directory"` → `echo "  CLI-ANYTHING-WEB.md: See plugin directory"`

- [ ] **Step 5: Update README.md**

Line 37: `Validate against WEB-HARNESS.md standards` → `Validate against CLI-ANYTHING-WEB.md standards`
Line 91: `See [WEB-HARNESS.md](./WEB-HARNESS.md)` → `See [CLI-ANYTHING-WEB.md](./CLI-ANYTHING-WEB.md)`

- [ ] **Step 6: Update SKILL.md**

Line 50: `**\`${CLAUDE_PLUGIN_ROOT}/WEB-HARNESS.md\`**` → `**\`${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md\`**`

- [ ] **Step 7: Verify no stale references remain**

```bash
cd cli-anything-web-plugin && grep -r "WEB-HARNESS" --include="*.md" --include="*.sh" .
```
Expected: 0 matches (empty output).

- [ ] **Step 8: Commit**

```bash
git add -A cli-anything-web-plugin/
git commit -m "chore: rename WEB-HARNESS.md to CLI-ANYTHING-WEB.md

Update all references across 10 files: 6 commands, setup script,
README, SKILL.md. No content changes — rename only."
```

---

### Task 2: Rewrite scripts/repl_skin.py

**Files:**
- Rewrite: `cli-anything-web-plugin/scripts/repl_skin.py`

- [ ] **Step 1: Write the complete repl_skin.py**

Replace the entire file with the web-adapted port. Key differences from reference:
- `software` parameter → `app`
- `self.software` → `self.app`
- `_ACCENT_COLORS`: web app brand colors (monday, notion, linear, etc.)
- History dir: `.cli-web-{self.app}` (not `.cli-anything-{self.software}`)
- Env var: `CLI_WEB_NO_COLOR` (not `CLI_ANYTHING_NO_COLOR`)
- Banner brand: `cli-web` (not `cli-anything`)
- `_ANSI_256_TO_HEX`: base dict from reference + 10 new web entries
- prompt_tokens class names: `class:app` (not `class:software`)
- get_prompt_style: `"app"` key (not `"software"`)

Complete file content:

```python
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
    across all CLI harnesses built with the web-harness methodology.
    """

    def __init__(self, app: str, version: str = "1.0.0",
                 history_file: str | None = None):
        """Initialize the REPL skin.

        Args:
            app: App name (e.g., "monday", "notion", "jira").
            version: CLI version string.
            history_file: Path for persistent command history.
                         Defaults to ~/.cli-web-<app>/history
        """
        self.app = app.lower().replace("-", "_")
        self.display_name = app.replace("_", " ").title()
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
```

- [ ] **Step 2: Smoke-test the import**

```bash
cd cli-anything-web-plugin && python3 -c "
import sys; sys.path.insert(0, 'scripts')
from repl_skin import ReplSkin
skin = ReplSkin('monday', version='1.0.0', history_file='/dev/null')
assert skin.app == 'monday'
assert skin.display_name == 'Monday'
assert skin.version == '1.0.0'
assert 'monday' in str(skin.accent)
# Verify prompt output (no-color mode for predictable output)
import os; os.environ['CLI_WEB_NO_COLOR'] = '1'
skin2 = ReplSkin('notion', version='2.0.0', history_file='/dev/null')
assert skin2._color == False
p = skin2.prompt(context='My Workspace', modified=True)
assert 'notion' in p
assert 'My Workspace*' in p
print('All checks passed')
"
```
Expected: `All checks passed`

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/scripts/repl_skin.py
git commit -m "feat: rewrite repl_skin.py with proper ReplSkin class

Port from reference with web-specific adaptations:
- Web app accent colors (monday, notion, linear, etc.)
- prompt_toolkit integration with FileHistory
- CLI_WEB_NO_COLOR env var
- Box-drawing banner with cli-web branding
- Full display method suite (success, error, table, etc.)"
```

---

## Chunk 2: Documentation Core (validate.md + CLI-ANYTHING-WEB.md)

### Task 3: Rewrite commands/validate.md

**Files:**
- Rewrite: `cli-anything-web-plugin/commands/validate.md`

- [ ] **Step 1: Write the complete validate.md**

Replace the entire file with the 8-category structure from the spec. The file must have:
- YAML frontmatter (name, description, argument-hint, allowed-tools)
- CRITICAL header referencing CLI-ANYTHING-WEB.md
- 8 categories with exact checks matching spec (50 total)
- Report format block
- Implementation steps for the agent

Full content:

```markdown
---
name: web-harness:validate
description: Validate a web-harness CLI against CLI-ANYTHING-WEB.md standards and best practices. Reports 8-category N/N check results.
argument-hint: <app-path>
allowed-tools: Bash(*), Read, Write, Edit
---

## CRITICAL: Read CLI-ANYTHING-WEB.md First

**Before validating, read `${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md`.** It is the single source of truth for all validation checks below. Every check in this command maps to a requirement in CLI-ANYTHING-WEB.md.

# Web-Harness: Validate Standards

Read the methodology SOP:
@${CLAUDE_PLUGIN_ROOT}/CLI-ANYTHING-WEB.md

Target: $ARGUMENTS

## Process

1. Parse the target path to extract `<app>` name
2. Resolve the `agent-harness/` root and `cli_web/<app>/` package path
3. Run all 8 categories of checks below
4. Print the report in the format shown at the bottom
5. Exit with summary: PASS if all 50 checks pass, FAIL otherwise

## Category 1: Directory Structure (6 checks)

*(checked against `agent-harness/` root)*

- [ ] `agent-harness/cli_web/<app>/` exists
- [ ] `agent-harness/<APP>.md` exists (software-specific SOP at harness root)
- [ ] `cli_web/` has NO `__init__.py` (namespace package)
- [ ] `<app>/` HAS `__init__.py`
- [ ] `core/`, `commands/`, `utils/`, `tests/` all present inside `cli_web/<app>/` (one atomic check)
- [ ] `setup.py` at `agent-harness/` root

## Category 2: Required Files (13 checks)

*(checked against `cli_web/<app>/`)*

- [ ] `README.md`
- [ ] `<app>_cli.py`
- [ ] `__main__.py`
- [ ] `core/client.py`
- [ ] `core/auth.py`
- [ ] `core/session.py`
- [ ] `core/models.py`
- [ ] `utils/repl_skin.py`
- [ ] `utils/output.py`
- [ ] `utils/config.py`
- [ ] `tests/TEST.md`
- [ ] `tests/test_core.py`
- [ ] `tests/test_e2e.py`

## Category 3: CLI Implementation Standards (6 checks)

- [ ] Uses Click framework with command groups (grep for `@click.group`)
- [ ] `--json` flag on every command (grep for `--json`)
- [ ] REPL mode — grep `<app>_cli.py` for `invoke_without_command=True`
- [ ] `repl_skin.py` used for banner, prompt, messages (grep for `ReplSkin`)
- [ ] `auth` command group with `login`, `status`, `refresh` subcommands
- [ ] Global session state (`pass_context=True` or module-level session object)

## Category 4: Core Module Standards (4 checks)

- [ ] `client.py`: has centralized auth header injection, exponential backoff, JSON parsing
- [ ] `auth.py`: has login, refresh, expiry check, secure storage
- [ ] `session.py`: has Session class with undo/redo stack
- [ ] `models.py`: has typed response models

## Category 5: Test Standards (8 checks)

- [ ] `TEST.md` has both plan (Part 1) and results (Part 2)
- [ ] Unit tests use `unittest.mock.patch` for HTTP — no real network calls
- [ ] E2E fixture tests replay captured responses from `tests/fixtures/`
- [ ] E2E live tests require auth — FAIL (not skip) without it
- [ ] `test_e2e.py` has `TestCLISubprocess` class
- [ ] Uses `_resolve_cli("cli-web-<app>")` — no hardcoded paths
- [ ] Subprocess `_run` does NOT set `cwd`
- [ ] Supports `CLI_WEB_FORCE_INSTALLED=1`

## Category 6: Documentation Standards (3 checks)

- [ ] `README.md`: has installation, auth setup, command reference, examples
- [ ] `<APP>.md`: has API map, data model, auth scheme, endpoint inventory
- [ ] No `CLI-ANYTHING-WEB.md` inside app package (it lives in plugin root)

## Category 7: PyPI Packaging Standards (5 checks)

- [ ] `find_namespace_packages(include=["cli_web.*"])` in setup.py
- [ ] Package name: `cli-web-<app>`
- [ ] Entry point: `cli-web-<app>=cli_web.<app>.<app>_cli:main`
- [ ] All imports use `cli_web.<app>.*` prefix
- [ ] `python_requires=">=3.10"`

## Category 8: Code Quality (5 checks)

- [ ] No syntax errors, no import errors (`python3 -c "import cli_web.<app>"`)
- [ ] No hardcoded auth tokens or API keys in source
- [ ] No hardcoded API base URLs or credential values in source
- [ ] No bare `except:` blocks
- [ ] Error messages include actionable guidance

## Report Format

Print results in this exact format:

```
Web Harness Validation Report
App: <app>
Path: <path>/agent-harness/cli_web/<app>

Directory Structure  (X/6 checks passed)
Required Files       (X/13 files present)
CLI Standards        (X/6 standards met)
Core Modules         (X/4 standards met)
Test Standards       (X/8 standards met)
Documentation        (X/3 standards met)
PyPI Packaging       (X/5 standards met)
Code Quality         (X/5 checks passed)

Overall: PASS|FAIL (X/50 checks)
```

For each FAIL, print a detail line below the category:
```
  FAIL: <check description> — <actionable fix suggestion>
```
```

- [ ] **Step 2: Verify the check counts**

```bash
cd cli-anything-web-plugin && grep -c "^\- \[ \]" commands/validate.md
```
Expected: `50`

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/commands/validate.md
git commit -m "feat: rewrite validate.md with 8-category N/N structure

50 checks across 8 categories: Directory Structure (6), Required Files (13),
CLI Standards (6), Core Modules (4), Test Standards (8), Documentation (3),
PyPI Packaging (5), Code Quality (5). Report format matches reference."
```

---

### Task 4: CLI-ANYTHING-WEB.md — Standalone Framing

**Files:**
- Modify: `cli-anything-web-plugin/CLI-ANYTHING-WEB.md`

- [ ] **Step 1: Replace Core Philosophy section**

Replace lines 11-33 (from `## Core Philosophy` through the end of `### Design Principles` including all 5 principles) with the standalone version from spec section 3b:

Old text starts with:
```
## Core Philosophy

CLI-Anything generates CLIs from **source code**.
Web-Harness generates CLIs from **network traffic**.
```

New text:
```
## Core Philosophy

Web-Harness builds production-grade Python CLI interfaces for closed-source web
applications by observing their live HTTP traffic. We capture real API calls directly
from the browser, reverse-engineer the API surface, and generate a stateful CLI that
sends authentic HTTP requests to the real service.

The output: a Python CLI under `cli_web/<app>/` with Click commands, `--json` output,
REPL mode, auth management, session state, and comprehensive tests.

### Design Principles

1. **Authentic Integration** — The CLI sends real HTTP requests to real servers.
   No mocks, no reimplementations, no toy replacements.
2. **Dual Interaction** — Every CLI has REPL mode + subcommand mode.
3. **Agent-Native** — `--json` flag on every command. `--help` self-docs.
   Agents discover tools via `which cli-web-<app>`.
4. **Zero Compromise** — Tests fail (not skip) when auth is missing or endpoints
   are unreachable.
5. **Structured Output** — JSON for agents, human-readable tables for interactive use.
```

- [ ] **Step 2: Replace Naming Conventions section**

Replace the two-column comparison table (lines 252-260, starts with `## Naming Conventions`) with:

```
## Naming Conventions

| Convention | Value |
|-----------|-------|
| CLI command | `cli-web-<app>` |
| Python namespace | `cli_web.<app>` |
| App-specific SOP | `<APP>.md` |
| Plugin slash command | `/web-harness` |
| Traffic capture dir | `traffic-capture/` |
| Auth config dir | `~/.config/cli-web-<app>/` |
```

- [ ] **Step 3: Verify no CLI-Anything comparison language remains**

```bash
cd cli-anything-web-plugin && grep -in "cli-anything" CLI-ANYTHING-WEB.md | grep -iv "CLI-ANYTHING-WEB"
```
Expected: 0 matches. If any remain (e.g., "matches CLI-Anything convention" on line 130 or 178), remove those comparison phrases.

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/CLI-ANYTHING-WEB.md
git commit -m "docs: apply standalone framing to CLI-ANYTHING-WEB.md

Remove CLI-Anything comparison language from Core Philosophy and
Naming Conventions. Plugin stands on its own — no parent dependency."
```

---

### Task 5: CLI-ANYTHING-WEB.md — Pipeline Gaps (Phases 5-7)

**Files:**
- Modify: `cli-anything-web-plugin/CLI-ANYTHING-WEB.md`

- [ ] **Step 1: Insert Phase 5 (Test Planning) after current Phase 4**

After the current `### Phase 4 — Implement (Code Generation)` section (ends around line 172), insert the new Phase 5 from spec section 3d. The full content is in the spec under "New Phase 5 content" — copy it verbatim.

- [ ] **Step 2: Renumber Phase 5 → Phase 6, Phase 6 → Phase 7, Phase 7 → Phase 8**

Change these headings:
- `### Phase 5 — Test (Write Tests)` → `### Phase 6 — Test (Write Tests)`
- `### Phase 6 — Document (Update TEST.md)` → `### Phase 7 — Document (Update TEST.md)`
- `### Phase 7 — Publish (Install to PATH)` → `### Phase 8 — Publish (Install to PATH)`

- [ ] **Step 3: Add Response Body Verification to Phase 6 (formerly Phase 5)**

After the testing rules list in Phase 6, add the Response Body Verification block from spec section 3e. Also add the round-trip test requirement sentence.

- [ ] **Step 4: Update Phase 7 (formerly Phase 6) to use two-part TEST.md structure**

Replace the current Phase 7 content with the updated process from spec section 3f. Key change: Phase 7 **appends** Part 2 to the existing TEST.md (which already has Part 1 from Phase 5). It does NOT write TEST.md from scratch.

- [ ] **Step 5: Verify phase numbering is sequential 1-8**

```bash
cd cli-anything-web-plugin && grep "^### Phase" CLI-ANYTHING-WEB.md
```
Expected output should show Phases 1 through 8 in order.

- [ ] **Step 6: Commit**

```bash
git add cli-anything-web-plugin/CLI-ANYTHING-WEB.md
git commit -m "docs: add Phase 5 Test Planning + fix pipeline gaps

Insert Phase 5 (Plan Tests / TEST.md Part 1) between Implement and Test.
Add Response Body Verification to Phase 6 (Test).
Update Phase 7 to append TEST.md Part 2. Pipeline is now 8 phases."
```

---

### Task 6: CLI-ANYTHING-WEB.md — Rules + Testing Strategy + Phase 8

**Files:**
- Modify: `cli-anything-web-plugin/CLI-ANYTHING-WEB.md`

- [ ] **Step 1: Insert Rules section after Critical Lessons, before Naming Conventions**

Find `## Naming Conventions` and insert before it a new `## Rules` section with the 9 bold-rule items from spec section 3g.

- [ ] **Step 2: Insert Testing Strategy section after Rules, before Naming Conventions**

After the Rules section, insert `## Testing Strategy` with the 4-layer table and `_resolve_cli` code block from spec section 3h.

- [ ] **Step 3: Expand Phase 8 (Publish) with namespace package explanation**

Add to Phase 8 the namespace package explanation from spec section 3i:
- Why namespace packages
- `cli_web/` has NO `__init__.py`
- `find_namespace_packages(include=["cli_web.*"])`
- Install verification with `CLI_WEB_FORCE_INSTALLED=1`

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/CLI-ANYTHING-WEB.md
git commit -m "docs: add Rules, Testing Strategy, expand Phase 8

9 enforcement rules, 4-layer testing strategy table with _resolve_cli
pattern, Phase 8 namespace package explanation."
```

---

## Chunk 3: Remaining Files

### Task 7: commands/web-harness.md — Success Criteria + Output Structure

**Files:**
- Modify: `cli-anything-web-plugin/commands/web-harness.md`

- [ ] **Step 1: Update phase count from 7 to 8**

Line 26: `Run ALL 7 phases in sequence` → `Run ALL 8 phases in sequence`

Update the progress table at the bottom to include Phase 5 (Plan Tests) and renumber Phases 5-7 to 6-8.

- [ ] **Step 2: Add Success Criteria section before Progress Tracking**

Insert before `## Progress Tracking`:

```markdown
## Success Criteria

The command succeeds when:
1. All core modules are implemented and functional (`client.py`, `auth.py`, `session.py`, `models.py`)
2. CLI supports both one-shot commands and REPL mode
3. `--json` output mode works for all commands
4. All tests pass (100% pass rate)
5. Subprocess tests use `_resolve_cli()` and pass with `CLI_WEB_FORCE_INSTALLED=1`
6. TEST.md contains both plan (Part 1) and results (Part 2)
7. README.md documents installation and usage
8. `setup.py` is created and local installation works
9. CLI is available in PATH as `cli-web-<app>`
```

- [ ] **Step 3: Add Output Structure section after Success Criteria**

Insert the directory tree from spec Change 4 `commands/web-harness.md` section.

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/commands/web-harness.md
git commit -m "docs: add Success Criteria + Output Structure to web-harness.md

9 success criteria, directory tree, update to 8-phase pipeline."
```

---

### Task 8: commands/refine.md — Gap-Present Step + Sections

**Files:**
- Modify: `cli-anything-web-plugin/commands/refine.md`

- [ ] **Step 1: Insert gap-present step**

Insert new step 4 between current Step 3 (Gap analysis) and Step 4 (Record new traffic):

```
4. **Present gap report**: Show the user the gap analysis results and confirm which gaps to address before proceeding with any recording or implementation
```

Renumber existing Steps 4-9 to Steps 5-10.

- [ ] **Step 2: Add Success Criteria section at the end**

```markdown
## Success Criteria

- All identified gaps have been addressed or explicitly deferred
- No existing commands are broken or have changed signatures
- New commands follow CLI-ANYTHING-WEB.md standards
- Full test suite passes (including new tests)
- TEST.md updated with new test coverage
- `<APP>.md` updated with new endpoints
```

- [ ] **Step 3: Add Notes section at the end**

```markdown
## Notes

- Refine is **incremental** — it only adds, never removes commands
- Always **present the gap report** before implementing changes
- Run the full test suite after changes to ensure no regressions
```

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/commands/refine.md
git commit -m "docs: add gap-present step + Success Criteria to refine.md"
```

---

### Task 9: commands/test.md — Subprocess Verification + Failure Handling

**Files:**
- Modify: `cli-anything-web-plugin/commands/test.md`

- [ ] **Step 1: Update Step 3 with subprocess verification**

After the existing Step 3 content (`CLI_WEB_FORCE_INSTALLED=1 python3 -m pytest ...`), add:

```
   After running, verify the subprocess backend was used:
   - Check output for `[_resolve_cli] Using installed command:` — this confirms
     the installed package is being tested, not the source fallback
   - If this line is absent, the installed CLI was not found in PATH
```

- [ ] **Step 2: Add Failure Handling section at the end**

```markdown
## Failure Handling

If any tests fail:
1. **Show the failures** — print the full pytest output with failure details
2. **Do NOT update TEST.md** — TEST.md should only contain passing results
3. **Analyze and suggest fixes** — provide specific guidance for each failure
4. **Offer to re-run** — ask the user if they want to fix and re-test
```

- [ ] **Step 3: Commit**

```bash
git add cli-anything-web-plugin/commands/test.md
git commit -m "docs: add subprocess verification + Failure Handling to test.md"
```

---

### Task 10: README.md — Standalone Framing + Fixes

**Files:**
- Modify: `cli-anything-web-plugin/README.md`

- [ ] **Step 1: Fix the title and tagline**

Replace lines 1-6:
```
# Web-Harness — CLI-Anything for the Web

**Make closed-source web apps Agent-Native via network traffic analysis.**

CLI-Anything generates CLIs from source code.
**Web-Harness generates CLIs from network traffic.**
```

With:
```
# Web-Harness — Agent-Native CLIs for Web Apps

**Build production-grade Python CLIs for closed-source web applications by capturing and analyzing their HTTP traffic.**
```

- [ ] **Step 2: Fix Quick Start (remove marketplace references)**

Replace lines 18-27 (the marketplace install) with:
```
```bash
# Copy plugin to Claude Code plugins directory
cp -r /path/to/cli-anything-web-plugin ~/.claude/plugins/web-harness

# Reload plugins in Claude Code
/reload-plugins

# Verify installation
/help web-harness

# Generate a CLI for any web app
/web-harness https://monday.com
```
```

- [ ] **Step 3: Add web-harness:list to Commands table**

Add this row to the Commands table:
```
| `/web-harness:list` | List all installed and generated `cli-web-*` CLIs |
```

- [ ] **Step 4: Fix Architecture section**

Replace line 73: `Follows CLI-Anything's proven conventions:` with `Generated package structure:`

- [ ] **Step 5: Commit**

```bash
git add cli-anything-web-plugin/README.md
git commit -m "docs: apply standalone framing + fix README.md

Remove CLI-Anything comparison, marketplace references.
Add web-harness:list command. Standalone tagline."
```

---

### Task 11: New verify-plugin.sh

**Files:**
- Create: `cli-anything-web-plugin/verify-plugin.sh`

- [ ] **Step 1: Write verify-plugin.sh**

```bash
#!/usr/bin/env bash
# verify-plugin.sh — Validate cli-anything-web-plugin structure
#
# Reports ALL checks (no fail-fast). Prints [PASS] or [FAIL] per check.
# Exits 0 if all pass, 1 if any fail.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "true" ]; then
        echo "[PASS] $desc"
        ((PASS++))
    else
        echo "[FAIL] $desc"
        ((FAIL++))
    fi
}

# plugin.json valid JSON
if python3 -c "import json; json.load(open('$SCRIPT_DIR/.claude-plugin/plugin.json'))" 2>/dev/null; then
    check ".claude-plugin/plugin.json is valid JSON" "true"
else
    check ".claude-plugin/plugin.json is valid JSON" "false"
fi

# CLI-ANYTHING-WEB.md exists
check "CLI-ANYTHING-WEB.md exists" "$([ -f "$SCRIPT_DIR/CLI-ANYTHING-WEB.md" ] && echo true || echo false)"

# All 6 command files
for cmd in web-harness record refine test validate list; do
    check "commands/$cmd.md exists" "$([ -f "$SCRIPT_DIR/commands/$cmd.md" ] && echo true || echo false)"
done

# scripts/repl_skin.py
check "scripts/repl_skin.py exists" "$([ -f "$SCRIPT_DIR/scripts/repl_skin.py" ] && echo true || echo false)"

# scripts/setup-web-harness.sh executable
if [ -f "$SCRIPT_DIR/scripts/setup-web-harness.sh" ] && [ -x "$SCRIPT_DIR/scripts/setup-web-harness.sh" ]; then
    check "scripts/setup-web-harness.sh is executable" "true"
else
    check "scripts/setup-web-harness.sh is executable" "false"
fi

# .mcp.json valid JSON
if python3 -c "import json; json.load(open('$SCRIPT_DIR/.mcp.json'))" 2>/dev/null; then
    check ".mcp.json is valid JSON" "true"
else
    check ".mcp.json is valid JSON" "false"
fi

# skills/web-harness-methodology/SKILL.md
check "skills/web-harness-methodology/SKILL.md exists" \
    "$([ -f "$SCRIPT_DIR/skills/web-harness-methodology/SKILL.md" ] && echo true || echo false)"

# PUBLISHING.md
check "PUBLISHING.md exists" "$([ -f "$SCRIPT_DIR/PUBLISHING.md" ] && echo true || echo false)"

# README.md
check "README.md exists" "$([ -f "$SCRIPT_DIR/README.md" ] && echo true || echo false)"

# Summary
TOTAL=$((PASS + FAIL))
echo ""
echo "$PASS/$TOTAL checks passed"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x cli-anything-web-plugin/verify-plugin.sh
```

- [ ] **Step 3: Run it to verify**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: All checks pass (14/14 or similar).

- [ ] **Step 4: Commit**

```bash
git add cli-anything-web-plugin/verify-plugin.sh
git commit -m "feat: add verify-plugin.sh for plugin structure validation"
```

---

### Task 12: New LICENSE

**Files:**
- Create: `cli-anything-web-plugin/LICENSE`

- [ ] **Step 1: Write MIT LICENSE**

```
MIT License

Copyright (c) 2026 CLI-Anything Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Commit**

```bash
git add cli-anything-web-plugin/LICENSE
git commit -m "docs: add MIT LICENSE"
```

---

### Task 13: Final Verification

- [ ] **Step 1: Run verify-plugin.sh**

```bash
cd cli-anything-web-plugin && bash verify-plugin.sh
```
Expected: All checks pass.

- [ ] **Step 2: Verify no stale WEB-HARNESS.md references**

```bash
cd cli-anything-web-plugin && grep -r "WEB-HARNESS" --include="*.md" --include="*.sh" .
```
Expected: 0 matches.

- [ ] **Step 3: Verify no CLI-Anything comparison language**

```bash
cd cli-anything-web-plugin && grep -rin "cli-anything" CLI-ANYTHING-WEB.md README.md | grep -iv "CLI-ANYTHING-WEB" | grep -iv "cli-anything-web"
```
Expected: 0 matches.

- [ ] **Step 4: Verify repl_skin.py imports cleanly**

```bash
cd cli-anything-web-plugin && python3 -c "import sys; sys.path.insert(0,'scripts'); from repl_skin import ReplSkin; print('OK')"
```
Expected: `OK`
