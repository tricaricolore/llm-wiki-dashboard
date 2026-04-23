# LLM Wiki Dashboard

Local-first dashboard for building project knowledge bases with Markdown,
Obsidian, Git, and an LLM assistant.

The goal is to let each team keep its knowledge base close to the project:
sources stay local in `raw/`, generated wiki pages live in `wiki/`, Obsidian is
used for reading and editing, and Git provides history, review, rollback, and
push to the project repository.

This project is based on Andrej Karpathy's
[LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## Intended Usage

Use this repository as a local tool/template, then create one clean wiki vault
per project.

```text
~/llm-wikis/llm-wiki-dashboard      tool/template repository
~/llm-wikis/project-alpha-wiki      project wiki vault
~/llm-wikis/project-beta-wiki       project wiki vault
~/llm-wikis/project-gamma-wiki      project wiki vault
```

Each project vault is independent:

- `raw/` contains immutable local source documents.
- `wiki/` contains LLM-maintained Obsidian pages.
- `ingest-reports/` records why an ingest changed the wiki.
- Git tracks every approved change.
- Teams decide when and where to push the vault.

## Requirements

- Python 3.10 or newer.
- Git.
- A browser.
- Obsidian, optional but recommended.
- Claude Code CLI for the current implementation.

Install Claude Code CLI:

```bash
npm install -g @anthropic-ai/claude-code
claude
```

The current code shells out to `claude -p`. A future provider layer can add
Copilot CLI or other local/enterprise-approved providers.

## Quick Start

Clone the tool repository:

```bash
mkdir -p ~/llm-wikis
cd ~/llm-wikis
git clone https://github.com/tricaricolore/llm-wiki-dashboard.git
cd llm-wiki-dashboard
```

Run the dashboard directly from this repository:

```bash
python dashboard/server.py
```

Open:

```text
http://localhost:8090
```

The repository root starts as a clean vault with three starter pages. Demo
content is kept under `examples/karpathy-demo/`.

## Create A Project Vault

For real use, create a separate vault for each project:

```bash
python scripts/init-vault.py ~/llm-wikis/project-alpha-wiki --git
cd ~/llm-wikis/project-alpha-wiki
python dashboard/server.py
```

Then open `http://localhost:8090` and open the same folder in Obsidian.

With `--git`, the script initializes a Git repository and creates an initial
commit. Add your project remote later:

```bash
git remote add origin <project-wiki-repo-url>
git push -u origin main
```

## Daily Workflow

1. Add original documents to `raw/`, or paste a source in the dashboard Ingest view.
2. Run ingest from the dashboard.
3. Review generated pages in `wiki/`, diffs, citations, and ingest report.
4. Open the vault in Obsidian for reading, linking, and manual edits.
5. Commit approved changes.
6. Push to the project wiki repository when the team wants to share them.

## Knowledge Model

```text
raw/              Original sources. Treat as immutable.
  |
  v
ingest            LLM reads sources and updates wiki pages.
  |
  v
wiki/             Obsidian Markdown pages with links and citations.
  |
  v
Git               Commit history, review, rollback, and team sync.
```

The important rule is that `raw/` is source-of-truth input. If a source is wrong,
do not edit it in place; create wiki notes that explain the correction.

## Dashboard Features

- Ingest: paste source content and generate wiki updates.
- Query: ask questions against the wiki and track files read.
- Search: local full-text search.
- Graph: force-directed view of wiki links.
- Provenance: citation coverage per page.
- History: ingest timeline backed by Git commits.
- Revert: undo an ingest commit.
- Lint: check wiki health and schema consistency.
- Reflect: generate periodic meta-analysis.
- Write and Compare: draft from wiki content or compare pages.

## Repository Layout

```text
raw/                       immutable local sources for this vault
wiki/                      LLM-maintained Obsidian pages
  index.md                 content catalog
  log.md                   activity timeline
  overview.md              starter overview page
ingest-reports/            one WHY report per ingest
reflect-reports/           meta-analysis reports
plans/                     planning notes
dashboard/                 local web app and API server
scripts/init-vault.py      create a clean vault for another project
examples/karpathy-demo/    sample raw/wiki/report content
CLAUDE.md                  wiki schema and LLM operating rules
.obsidian/                 Obsidian vault settings
```

## Configuration

Environment variables:

```bash
CLAUDE_TIMEOUT=1200 python dashboard/server.py
CLAUDE_QUICK_TIMEOUT=30
CLAUDE_TOOLS=Edit,Write,Read,Glob,Grep
```

Project rules live in `CLAUDE.md`. Edit it to change frontmatter rules,
citation rules, contradiction handling, ingest workflow, and lint behavior.

## Local-First Notes

- The dashboard runs on `localhost`.
- Source documents are read from the local filesystem.
- No central database is required.
- Git push is explicit and controlled by the project team.
- Do not put confidential sources in a remote repository unless that repository
  is approved for that data.

## Demo Content

The original sample vault is preserved in:

```text
examples/karpathy-demo/
```

Use it only for reference, screenshots, or experiments. New project vaults
created with `scripts/init-vault.py` do not include demo sources or pages.

## Troubleshooting

### Claude CLI timeout

Increase the timeout for larger ingests:

```bash
CLAUDE_TIMEOUT=1800 python dashboard/server.py
```

You can also switch to a faster model from the dashboard header.

### Claude CLI not connected

Run this in a terminal:

```bash
claude
```

Complete login/authentication, then restart the dashboard.

### Obsidian vault not registered

Open the generated project vault folder directly from Obsidian. The dashboard can
also register the current folder in Obsidian from the status area.

### Empty or invalid JSON response

Restart the server and check the terminal output. The server is a local Python
process, so API errors are printed there.

## Current Limitations

- The LLM provider is currently Claude CLI only.
- There is no multi-user web authentication.
- Collaboration is expected to happen through Git, not through a central server.
- Enterprise Copilot support requires a provider abstraction around the current
  direct `claude` calls.

## Credits

- Pattern: [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
- Ancestor idea: [Vannevar Bush, "As We May Think"](https://en.wikipedia.org/wiki/As_We_May_Think), 1945.
- Original implementation: Memex / Claude Code based dashboard.
