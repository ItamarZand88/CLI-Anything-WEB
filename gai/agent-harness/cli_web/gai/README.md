# cli-web-gai

CLI for Google AI Mode — submit questions and get AI-generated answers with source references, powered by a headless Playwright browser.

## Installation

```bash
pip install cli-web-gai
```

## Usage

### Search

```bash
# Ask a question
cli-web-gai search ask "What is quantum computing?"

# Ask with JSON output
cli-web-gai search ask "Best Python frameworks" --json

# Ask in a specific language
cli-web-gai search ask "What is machine learning?" --lang he

# Show the browser window (for debugging or solving CAPTCHAs)
cli-web-gai search ask "Explain DNS" --headed

# Set a custom timeout (seconds)
cli-web-gai search ask "History of the internet" --timeout 45
```

### Follow-up Questions

After an initial `ask`, you can ask follow-up questions within the same session:

```bash
cli-web-gai search followup "Tell me more about that"
cli-web-gai search followup "How is it used in practice?" --json
```

Follow-up questions maintain conversation context from the previous query in the same session.

## JSON Output

Every command supports `--json` for structured output:

```bash
cli-web-gai search ask "capital of France" --json
```

Returns:

```json
{
  "success": true,
  "data": {
    "query": "capital of France",
    "answer": "The capital of France is Paris...",
    "sources": [
      {"title": "Wikipedia", "url": "https://en.wikipedia.org/wiki/Paris", "snippet": "..."}
    ],
    "follow_up_prompt": "What are the main attractions in Paris?"
  }
}
```

Errors also return structured JSON:

```json
{
  "error": true,
  "code": "CAPTCHA_REQUIRED",
  "message": "Google presented a CAPTCHA. Please solve it in a browser and try again."
}
```

## REPL Mode

Run without arguments to enter interactive mode:

```bash
cli-web-gai
```

REPL shortcuts:
- `ask <query>` — same as `search ask <query>`
- `followup <query>` — same as `search followup <query>`
- `help` — show available commands
- `exit` / `quit` — exit the REPL

## Authentication

No authentication is required. Google AI Mode is publicly accessible.

Note: Google rate-limits headless browsers. If you encounter a CAPTCHA, use `--headed` to open a visible browser window and solve it manually.

## Testing

```bash
cd gai/agent-harness
pip install -e .
python -m pytest cli_web/gai/tests/ -v -s
```

Set `CLI_WEB_FORCE_INSTALLED=1` for subprocess tests to find the installed CLI binary.

## Protocol

- **Website:** google.com/search (AI Mode)
- **Protocol:** Browser-rendered (Playwright headless Chromium)
- **Auth:** None
