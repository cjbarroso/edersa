# Agent instructions

This repository contains a portable, read-only EDERSA billing automation.

For any task involving EDERSA invoices, debt, bills, or account data:

1. Read `.agents/skills/run-edersa-portal/SKILL.md` before running the project.
2. Work from the repository root and use the existing Python entry points.
3. Keep `.env`, `cookies.json`, account data, and payment barcodes local and out of logs.
4. Do not submit payments or modify portal data.

The `SKILL.md` file is the canonical instructions bundle. Agents that do not have
automatic skill discovery, including Hermes deployments with a custom skill loader,
should load that file explicitly or install it into their configured skill directory.
See [`docs/INSTALL_AGENT_SKILL.md`](docs/INSTALL_AGENT_SKILL.md) for the portable
installation procedure and the Hermes-specific `--skills-dir` form.
