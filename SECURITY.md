# Security Policy

## Supported Versions

Only the latest `main` branch is actively maintained. We recommend always pulling the latest version.

| Branch | Supported |
|--------|-----------|
| `main` (latest) | Yes |
| Older commits | No |

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **GitHub Security Advisories** (preferred): Go to [Security Advisories](https://github.com/ItamarZand88/CLI-Anything-WEB/security/advisories) and create a new draft advisory.
2. **Email**: Contact the maintainer directly via GitHub profile.

Please do **not** open a public issue for security vulnerabilities. We aim to respond within 48 hours and provide a fix or mitigation within 7 days.

## Security Considerations

CLI-Anything-Web captures live HTTP traffic from real websites and stores authentication credentials locally. Understanding what gets stored and where is important.

### Sensitive Files

| File / Directory | Contains | Protection |
|-----------------|----------|------------|
| `auth.json` | Session cookies from browser login | Stored with `chmod 600`, gitignored (`**/auth.json`) |
| `traffic-capture/` | Raw HTTP requests/responses from recording sessions | Gitignored (`**/traffic-capture/`) |
| `.playwright-cli/` | Full browser session data including cookies and storage state | Gitignored (`.playwright-cli/`) |
| `playwright-state.json` | Browser context state with session data | Gitignored (`**/playwright-state.json`) |

### How Credentials Are Handled

- **Never hardcoded**: Generated CLIs read auth from `~/.config/cli-web-<app>/auth.json`, never from source code.
- **File permissions**: `auth.json` is created with `chmod 600` (owner read/write only).
- **Environment variable fallback**: For CI/CD, credentials can be passed via `CLI_WEB_<APP>_AUTH_JSON` environment variables instead of files on disk.
- **No credentials in git**: The `.gitignore` blocks `**/auth.json`, `**/traffic-capture/`, `.playwright-cli/`, `.env`, and `*.credentials.json`.

### What the `.gitignore` Protects

The repository `.gitignore` is configured to block all sensitive artifacts from being committed:

```
# Auth credentials
**/auth.json
*.credentials.json
.env
.env.*

# Traffic captures (may contain auth headers, cookies, tokens)
**/traffic-capture/

# Browser session data
.playwright-cli/
**/playwright-state.json
```

If you add a new CLI to the repo, these patterns apply automatically. You do not need to add per-CLI ignore rules.

### Traffic Captures

When you run `/cli-anything-web <url>` or `/cli-anything-web:record <url>`, the plugin records all HTTP traffic between the browser and the target site. These captures may contain:

- Authentication headers (`Authorization`, `Cookie`)
- Session tokens and CSRF tokens
- API keys embedded in request URLs or headers
- Personal data in API responses

Traffic captures are stored in `<app>/traffic-capture/` and are gitignored. Delete them after you finish generating a CLI if you no longer need them.

## Best Practices

### For Contributors

- **Never commit `auth.json` or traffic captures.** Run `git status` before committing to verify no sensitive files are staged.
- **Review generated code for leaked secrets.** After the plugin generates a CLI, check that no tokens, cookies, or personal data ended up in source files.
- **Use environment variables in CI.** Set `CLI_WEB_<APP>_AUTH_JSON` instead of copying `auth.json` into CI runners.

### For Users

- **Rotate cookies after sharing traces.** If you shared a traffic capture or browser trace with someone, log out and back in to invalidate the captured session.
- **Keep `auth.json` local.** Do not copy it to shared drives, paste it in chat, or include it in bug reports.
- **Use the CLI on trusted networks.** Generated CLIs make HTTP requests to real production services. Avoid using them on untrusted networks without HTTPS.
- **Delete old auth files.** If you stop using a CLI, remove its auth file: `rm ~/.config/cli-web-<app>/auth.json`
- **Review permissions.** On shared machines, verify that `~/.config/cli-web-<app>/auth.json` is not world-readable: `ls -la ~/.config/cli-web-<app>/auth.json` should show `-rw-------`.
