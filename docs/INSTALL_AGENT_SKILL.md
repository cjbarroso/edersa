# Install the EDERSA agent skill

This repository contains the reusable `run-edersa-portal` skill at:

```text
.agents/skills/run-edersa-portal
```

The procedure below is intended for an AI agent with GitHub access to the private
repository `cjbarroso/edersa`.

## Prerequisites

- Git is installed.
- The agent can authenticate to GitHub and read `cjbarroso/edersa`.
- Python 3.10 or newer is available for the installer.

The GitHub credential is used only to clone the repository. The installer does not
read EDERSA credentials, `.env`, `cookies.json`, or any portal session data.

## Install from GitHub

With the GitHub CLI:

```bash
gh repo clone cjbarroso/edersa edersa
python edersa/scripts/install_skill.py --repo edersa
```

If the agent uses Git credentials without the GitHub CLI, clone the same repository
with Git and run the installer from the checkout:

```bash
git clone --depth 1 --branch master https://github.com/cjbarroso/edersa.git edersa
python edersa/scripts/install_skill.py --repo edersa
```

The installer validates that `.agents/skills/run-edersa-portal/SKILL.md` exists and
copies the complete skill, including `agents/openai.yaml`.

## Installation location

By default, the skill is installed at:

1. `$CODEX_HOME/skills/run-edersa-portal` when `CODEX_HOME` is set.
2. `~/.codex/skills/run-edersa-portal` otherwise.

For another agent or a custom skills directory, provide the parent directory:

```bash
python edersa/scripts/install_skill.py \
  --repo edersa \
  --skills-dir /path/to/agent/skills
```

The final directory will be `/path/to/agent/skills/run-edersa-portal`.

## Update an existing installation

Pull the new repository revision and explicitly allow replacement of the installed
skill:

```bash
git -C edersa pull
python edersa/scripts/install_skill.py --repo edersa --force
```

Without `--force`, the installer stops instead of overwriting an existing skill.

## Verify the installation

Check that the skill entry point exists:

```bash
test -f ~/.codex/skills/run-edersa-portal/SKILL.md
```

For a custom destination, replace the path with the value passed to `--skills-dir`.
Start a new agent session or reload its skills, then invoke:

```text
$run-edersa-portal
```

The skill runs the repository's read-only EDERSA automation. It must not be used to
submit payments or modify portal data.

## Troubleshooting

- `gh repo clone` fails: run `gh auth status` and verify that the authenticated account can read `cjbarroso/edersa`.
- `git clone` fails: verify the agent's GitHub credential helper and repository access.
- The target already exists: rerun with `--force` only when replacing that exact skill installation is intended.
- The agent does not discover the skill: confirm that `SKILL.md` is directly under the installed `run-edersa-portal` directory and start a fresh agent session.
