# Quick Start — CLI-Anything-Web

**From zero to a working CLI in under 10 minutes.**

## Step 1: Prerequisites (30 seconds)

Verify Node.js is installed (needed for playwright-cli):
```bash
npx @playwright/cli@latest --version
```
If this fails, install Node.js from https://nodejs.org/

## Step 2: Generate a CLI (5-10 minutes)

```bash
/cli-anything-web https://your-web-app.com
```

Claude will:
1. Open Chrome with your login session
2. Ask you to log in if needed
3. Systematically browse the app
4. Capture all API traffic
5. Analyze endpoints and data models
6. Generate a complete Python CLI
7. Install it to your PATH

## Step 3: Use the CLI

```bash
# See all commands
cli-web-yourapp --help

# Authenticate
cli-web-yourapp auth login

# Use commands
cli-web-yourapp resources list --json
cli-web-yourapp resources create --name "New Item"

# Enter REPL
cli-web-yourapp
```

## Step 4: Expand Coverage

If the first pass missed some features:

```bash
# Broad gap analysis
/cli-anything-web:refine ./yourapp

# Targeted expansion
/cli-anything-web:refine ./yourapp "reporting and export features"
```

## Step 5: Validate

```bash
/cli-anything-web:validate ./yourapp
```

## Tips

- **More browsing = better CLI**: The more features you exercise during recording, the more complete the generated CLI
- **Auth matters**: Make sure you're logged in before Claude starts recording
- **Iterate**: Run `/cli-anything-web:refine` multiple times to expand coverage
- **Test live**: E2E tests hit real API — verify they pass against the actual service
