# Advanced Usage

Advanced features and configuration for agent-browser. For the core workflow and essential commands,
see SKILL.md.

## Security

All security features are opt-in. By default, agent-browser imposes no restrictions on navigation,
actions, or output.

### Content Boundaries (Recommended for AI Agents)

Enable `--content-boundaries` to wrap page-sourced output in markers that help LLMs distinguish tool
output from untrusted page content:

```bash
export AGENT_BROWSER_CONTENT_BOUNDARIES=1
agent-browser snapshot
# Output:
# --- AGENT_BROWSER_PAGE_CONTENT nonce=<hex> origin=https://example.com ---
# [accessibility tree]
# --- END_AGENT_BROWSER_PAGE_CONTENT nonce=<hex> ---
```

### Domain Allowlist

Restrict navigation to trusted domains. Wildcards like `*.example.com` also match the bare domain
`example.com`. Sub-resource requests, WebSocket, and EventSource connections to non-allowed domains
are also blocked. Include CDN domains your target pages depend on:

```bash
export AGENT_BROWSER_ALLOWED_DOMAINS="example.com,*.example.com"
agent-browser open https://example.com        # OK
agent-browser open https://malicious.com       # Blocked
```

### Action Policy

Use a policy file to gate destructive actions:

```bash
export AGENT_BROWSER_ACTION_POLICY=./policy.json
```

Example `policy.json`:

```json
{ "default": "deny", "allow": ["navigate", "snapshot", "click", "scroll", "wait", "get"] }
```

Auth vault operations (`auth login`, etc.) bypass action policy but domain allowlist still applies.

### Output Limits

Prevent context flooding from large pages:

```bash
export AGENT_BROWSER_MAX_OUTPUT=50000
```

## Diffing (Verifying Changes)

Use `diff snapshot` after performing an action to verify it had the intended effect. This compares
the current accessibility tree against the last snapshot taken in the session.

```bash
# Typical workflow: snapshot -> action -> diff
agent-browser snapshot -i          # Take baseline snapshot
agent-browser click @e2            # Perform action
agent-browser diff snapshot        # See what changed (auto-compares to last snapshot)
```

For visual regression testing or monitoring:

```bash
# Save a baseline screenshot, then compare later
agent-browser screenshot baseline.png
# ... time passes or changes are made ...
agent-browser diff screenshot --baseline baseline.png

# Compare staging vs production
agent-browser diff url https://staging.example.com https://prod.example.com --screenshot
```

`diff snapshot` output uses `+` for additions and `-` for removals, similar to git diff. `diff
screenshot` produces a diff image with changed pixels highlighted in red, plus a mismatch
percentage.

## Timeouts and Slow Pages

The default timeout is 25 seconds. Override with the `AGENT_BROWSER_DEFAULT_TIMEOUT` environment
variable (value in milliseconds). For slow websites or large pages, use explicit waits:

```bash
agent-browser wait --load networkidle           # Wait for network activity to settle
agent-browser wait "#content"                    # Wait for specific element
agent-browser wait --url "**/dashboard"          # Wait for URL pattern after redirects
agent-browser wait --fn "document.readyState === 'complete'"  # JavaScript condition
agent-browser wait 5000                          # Fixed duration (last resort)
```

When dealing with consistently slow websites, use `wait --load networkidle` after `open` to ensure
the page is fully loaded before taking a snapshot.

## JavaScript Dialogs (alert / confirm / prompt)

When a page opens a JavaScript dialog, it blocks all other browser commands until dismissed. If
commands start timing out unexpectedly, check for a pending dialog:

```bash
agent-browser dialog status                      # Check if dialog is blocking
agent-browser dialog accept                      # Accept (dismiss alert / click OK)
agent-browser dialog accept "my input"           # Accept prompt with input text
agent-browser dialog dismiss                     # Dismiss (click Cancel)
```

When a dialog is pending, all command responses include a `warning` field indicating the dialog type
and message.

## Annotated Screenshots (Vision Mode)

Use `--annotate` to take a screenshot with numbered labels overlaid on interactive elements. Each
label `[N]` maps to ref `@eN`. This also caches refs, so you can interact immediately without a
separate snapshot.

```bash
agent-browser screenshot --annotate
# Output includes the image path and a legend:
#   [1] @e1 button "Submit"
#   [2] @e2 link "Home"
#   [3] @e3 textbox "Email"
agent-browser click @e2              # Click using ref from annotated screenshot
```

Use annotated screenshots when:

- The page has unlabeled icon buttons or visual-only elements
- You need to verify visual layout or styling
- Canvas or chart elements are present (invisible to text snapshots)
- You need spatial reasoning about element positions

## Semantic Locators (Alternative to Refs)

When refs are unavailable or unreliable, use semantic locators:

```bash
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "user@test.com"
agent-browser find role button click --name "Submit"
agent-browser find placeholder "Search" type "query"
agent-browser find testid "submit-btn" click
```

## JavaScript Evaluation (eval)

Use `eval` to run JavaScript in the browser context. **Shell quoting can corrupt complex
expressions** — use `--stdin` or `-b` to avoid issues.

```bash
# Simple expressions work with regular quoting
agent-browser eval 'document.title'
agent-browser eval 'document.querySelectorAll("img").length'

# Complex JS: use --stdin with heredoc (RECOMMENDED)
agent-browser eval --stdin <<'EVALEOF'
JSON.stringify(
  Array.from(document.querySelectorAll("img"))
    .filter(i => !i.alt)
    .map(i => ({ src: i.src.split("/").pop(), width: i.width }))
)
EVALEOF

# Alternative: base64 encoding (avoids all shell escaping issues)
agent-browser eval -b "$(echo -n 'complex js here' | base64)"
```

**Rules of thumb:**

- Single-line, no nested quotes → regular `eval 'expression'` with single quotes
- Nested quotes, arrow functions, template literals → use `eval --stdin <<'EVALEOF'`
- Programmatic/generated scripts → use `eval -b` with base64

## Configuration File

Create `agent-browser.json` in the project root for persistent settings:

```json
{
  "headed": true,
  "proxy": "http://localhost:8080",
  "profile": "./browser-data"
}
```

Priority (lowest to highest): `~/.agent-browser/config.json` < `./agent-browser.json` < env vars <
CLI flags. Use `--config <path>` or `AGENT_BROWSER_CONFIG` env var for a custom config file. All CLI
options map to camelCase keys (e.g., `--executable-path` → `"executablePath"`).

## Browser Engine Selection

Use `--engine` to choose a local browser engine. The default is `chrome`.

```bash
agent-browser --engine lightpanda open example.com
export AGENT_BROWSER_ENGINE=lightpanda
```

Supported engines:

- `chrome` (default) — Chrome/Chromium via CDP
- `lightpanda` — Lightpanda headless browser via CDP (10x faster, 10x less memory than Chrome)

Lightpanda does not support `--extension`, `--profile`, `--state`, or `--allow-file-access`. Install
Lightpanda from <https://lightpanda.io/docs/open-source/installation>.

## Observability Dashboard

The dashboard is a standalone background server that shows live browser viewports, command activity,
and console output for all sessions.

```bash
agent-browser dashboard install                  # Install once
agent-browser dashboard start                    # Start (background, port 4848)
agent-browser open example.com                   # Sessions auto-visible
agent-browser dashboard stop                     # Stop
```

The dashboard runs independently on port 4848 (configurable with `--port`).

## Session Management and Cleanup

When running multiple agents concurrently, always use named sessions to avoid conflicts:

```bash
agent-browser --session agent1 open site-a.com
agent-browser --session agent2 open site-b.com
agent-browser session list
```

Always close sessions when done to avoid leaked processes:

```bash
agent-browser close                    # Close default session
agent-browser --session agent1 close   # Close specific session
agent-browser close --all              # Close all active sessions
```

Auto-shutdown after inactivity (useful for CI):

```bash
AGENT_BROWSER_IDLE_TIMEOUT_MS=60000 agent-browser open example.com
```
