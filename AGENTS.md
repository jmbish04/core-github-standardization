<!-- BEGIN colby-ecosystem: managed by pull-agents, do not edit inside this block -->
## Machine-wide agent briefings (synced — do not edit here)

Pulled from `jmbish04/colby-ecosystem` by `.github/workflows/agents-sync.yml`, right-sized to this
repo's stack. Read them before your first load-bearing change; where they and the
notes below this block disagree, they win. Edit them in `jmbish04/colby-ecosystem`, never here.

@.agents/ecosystem/AGENTS.md
@.agents/ecosystem/AGENTS-maestro.md
@.agents/ecosystem/AGENTS-github.md
@.agents/ecosystem/AGENTS-cloudflare-workers.md
@.agents/ecosystem/AGENTS-frontend.md
@.agents/ecosystem/AGENTS-python.md
@.agents/ecosystem/AGENTS-mcp.md

The scripts in `scripts/` carrying a `colby-ecosystem: managed script` banner come from there too.
Use them rather than writing another: `scripts/gh.mjs` is the GitHub entry point
and wraps the `gh-tools` CLI, which already solves the auth this machine trips on.
`scripts/run.sh` is the verbose step runner: source it and put every step through
`run`, so a script that fails on its first line says so instead of reading as a
success. `bash scripts/run.sh --self-check` proves its own checks can fail.

Work is tracked in **colby-maestro** (`https://colby-maestro.hacolby.workers.dev/mcp`,
bearer `$(tokens show WORKER_API_KEY --value-only)`) — never in this repo and never
in colby-ecosystem, which only stores config. Refresh this block with
`.agents/ecosystem/pull-agents`.

Before a step these briefings do not plainly cover — a credential, a host, a database, a deploy, a backup — search **playbooks** on colby-maestro first, on a half-remembered fragment rather than a title, and say in the worklog what you found; write one when you had to work something out that nobody had written down (`.agents/ecosystem/AGENTS.md`, "Write down what you worked out").
<!-- END colby-ecosystem -->

# core-github-standardization

Repo-local agent notes go below the block above.
