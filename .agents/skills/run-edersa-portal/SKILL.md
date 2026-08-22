---
name: run-edersa-portal
description: Run this repository's read-only EDERSA portal automation to authenticate, refresh billing data, and return invoices or pending debt as structured JSON. Use only for this project; never use it to make or initiate payments.
---

# Run EDERSA Portal

Use this skill when the user asks for EDERSA invoices, debt, unpaid bills, account billing data, or a JSON refresh from this repository.

This is an agent-neutral instruction bundle. It requires only shell access to the
repository, Python, and network access to the EDERSA portals; it does not depend on
Codex, a specific model, a proprietary tool, or a `$skill-name` invocation syntax.
Agents that do not discover skills automatically should load this file explicitly.

## Agent compatibility

- Treat this `SKILL.md` as the canonical runtime contract. The root `AGENTS.md` is a short adapter for agents that load repository instructions instead of skills.
- Hermes and other agents with a configurable skills root should install this directory with `scripts/install_skill.py --skills-dir <agent-skills-root>` or point their loader directly at `.agents/skills/run-edersa-portal`.
- `agents/openai.yaml` is optional interface metadata for compatible hosts. Other agents may ignore it; the execution instructions are entirely in this file.
- Invoke the project with ordinary shell commands and report the resulting JSON summary. Do not assume `$run-edersa-portal`, `gh`, or `CODEX_HOME` exists at runtime.

## Scope and safety

- Work from the repository root, where `get_invoices.py`, `login.py`, and `edersa_client.py` are located.
- This integration is read-only. Do not click payment controls, submit payment forms, replay payment events, or call any endpoint other than the existing login and authenticated read paths.
- Access only accounts the user is authorized to access and follow the portal's terms.
- Treat `.env`, `cookies.json`, account numbers, addresses, invoice identifiers, and `barra1`/`barra2` payment barcodes as secrets or personal data. Never print them in diagnostics, commit them, or include them in a broad tool log. Summarize counts and statuses instead.
- Do not ask the user to paste a password or cookie into chat. If configuration is missing, tell the user which local `.env` setting is missing.

## Choose the execution path

1. Prefer the existing virtual environment. On Windows use `.venv\\Scripts\\python.exe`; on macOS/Linux use `.venv/bin/python`. If it does not exist, create an isolated environment and install `requirements.txt`; install Playwright Chromium once before the first browser login. Ask for authorization if the environment requires network access or an external install.
2. For a complete refresh, account discovery, or an expired session, run the main entry point with the selected interpreter:

   ```text
   python get_invoices.py > all.json
   python get_invoices.py --pending > pending.json
   ```

   The first command writes all invoices for every account discovered during login. The second writes only unpaid items while retaining `pending_total_count`. The run saves the authenticated portal cookies to the git-ignored `cookies.json`. When the user explicitly wants the JSON in the conversation, read and summarize the file selectively; do not echo the raw payload by default.

3. For a fast refresh of one account when `cookies.json` is still valid, run:

   ```text
   python edersa_client.py > debt.json
   ```

   This path needs `EDERSA_HOME_QS` in the local `.env`, or an equivalent environment variable. The value identifies the account context and has the form `<accountKey>,<cliente>,<suffix>,AIngreso,`; the server ultimately keys the read by `cliente,suffix`.

4. Use `login.py` alone only when the user specifically asks to refresh the session or inspect the login handoff. `get_invoices.py` already performs that full browser login and handoff when needed.

Replace `python` in the examples with the selected virtual-environment interpreter. Keep JSON output separate from diagnostics; save personal-data results only to the git-ignored output names already listed in `.gitignore` (`all.json`, `pending.json`, or `debt.json`). Avoid sending raw JSON to the agent transcript unless the user explicitly requests it.

## Local configuration

- Login reads `.env` directly. Prefer `EDERSA_USER` and `EDERSA_PASS`; the legacy aliases `USERNAME` and `PASSWORD` are also supported. Login is by email.
- `EDERSA_HEADLESS=1` is the default. Set it to `0` only for local browser debugging.
- The browser flow discovers all accounts from the Oficina Virtual home, follows the `Ir a Facturas y Pagos` SSO handoff, captures the `pagos.edersa.com.ar` cookies, and then performs authenticated GETs for the debt data.
- The browser-free client reads cookies in this priority order: `EDERSA_COOKIE`, `EDERSA_COOKIES_FILE` (default `cookies.json`), then individual cookie variables. Do not expose any of these values.

Do not overwrite an existing `.env` or `cookies.json` to repair configuration. Inspect only whether the files exist and contain the required keys, then ask the user to update local values if needed.

## Validate and report

- Parse stdout as JSON; do not treat a successful process exit alone as a successful data read.
- For `get_invoices.py`, verify the result has `accounts` and `pending_total_count`. Report account count, invoice count, and pending count; omit addresses, identifiers, barcodes, and full invoice payloads unless the user explicitly requests a local file or a specific field.
- For `edersa_client.py`, verify `facturas` and `cantidad` are present and consistent. A zero-invoice result with no `EDERSA_HOME_QS` is not a reliable account read; set the account context or use the full login flow.
- If the client reports an expired session, missing cookies, missing `GXState`, or no portal handoff, run the full `get_invoices.py` flow once. If it still fails, report the concrete failure and the safe next action; do not retry indefinitely.
- If Playwright is missing, install the declared dependencies in the isolated environment and Chromium, then retry once. Do not modify application code merely to work around an environment problem.
