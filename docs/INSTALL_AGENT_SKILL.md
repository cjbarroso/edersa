# Install the EDERSA agent skill

This repository contains the portable `run-edersa-portal` skill at:

```text
.agents/skills/run-edersa-portal
```

The procedure below is intended for an AI agent that can reach the public
repository `cjbarroso/edersa`.

## Prerequisites

- Git is installed.
- The agent can reach GitHub over the network. No GitHub credential is required.
- Python 3.10 or newer is available for the installer.

The installer does not read EDERSA credentials, `.env`, `cookies.json`, or any
portal session data.

The canonical payload is the directory containing `SKILL.md`. The optional
`agents/openai.yaml` file provides interface metadata for hosts that support it;
Hermes and other agents may ignore that file.

## Install from GitHub

With Git:

```bash
git clone --depth 1 --branch master https://github.com/cjbarroso/edersa.git edersa
python edersa/scripts/install_skill.py --repo edersa
```

The GitHub CLI is optional. If it is already available, this is equivalent:

```bash
gh repo clone cjbarroso/edersa edersa
python edersa/scripts/install_skill.py --repo edersa
```

The installer validates that `.agents/skills/run-edersa-portal/SKILL.md` exists and
copies the complete skill, including `agents/openai.yaml`.

## Installation location

When no destination is provided, the installer checks these locations in order:

1. `AGENT_SKILLS_DIR`.
2. `CODEX_SKILLS_DIR`.
3. `$CODEX_HOME/skills` when `CODEX_HOME` is set.
4. An existing `~/.codex/skills` directory.
5. `~/.agents/skills` as the generic fallback.

For Hermes or another agent with a custom skills directory, always pass the
configured parent directory explicitly:

```bash
python edersa/scripts/install_skill.py \
  --repo edersa \
  --skills-dir /path/to/hermes/skills
```

The final directory will be `/path/to/hermes/skills/run-edersa-portal`.

If an agent loads project-local skills, no global installation is needed: configure
its loader to read `.agents/skills/run-edersa-portal/SKILL.md` from the checkout.
If it has no skill registry, load that file as the agent's task instructions. The
root `AGENTS.md` points agents to the same canonical file.

## Update an existing installation

Pull the new repository revision and explicitly allow replacement of the installed
skill:

```bash
git -C edersa pull
python edersa/scripts/install_skill.py --repo edersa --force
```

Without `--force`, the installer stops instead of overwriting an existing skill.

## Verify the installation

Check that the skill entry point exists in the selected skills directory:

```bash
test -f /path/to/agent/skills/run-edersa-portal/SKILL.md
```

Start a new agent session or reload its skills. Ask the agent for EDERSA invoices
or pending debt; it should read `SKILL.md` and run the repository's normal entry
points rather than depend on a vendor-specific command.

The skill runs the repository's read-only EDERSA automation. It must not be used to
submit payments or modify portal data.

## Troubleshooting

- `gh repo clone` fails: use the public HTTPS `git clone` command or verify the network connection.
- `git clone` fails: verify the network connection and that the agent can reach GitHub.
- The target already exists: rerun with `--force` only when replacing that exact skill installation is intended.
- The agent does not discover the skill: confirm that `SKILL.md` is directly under the installed `run-edersa-portal` directory, configure the agent's skill loader, and start a fresh session.
