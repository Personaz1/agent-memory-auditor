# agent-memory-auditor

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)

OpenClaw plugin overlay for auditing agent memory quality (duplicates, stale facts, contradictions).

## Summary

`agent-memory-auditor` scans markdown memory files and outputs a practical quality report.

## Features

- OpenClaw plugin packaging (`openclaw.plugin.json`)
- Native slash command: `/memory-audit`
- CLI scanner with score (0–100)
- Findings: duplicates, stale candidates, contradiction hints
- Markdown report generation

## Install as OpenClaw plugin

```bash
git clone https://github.com/Personaz1/agent-memory-auditor.git
cd agent-memory-auditor
openclaw plugins install .
openclaw plugins enable agent-memory-auditor
openclaw gateway restart
```

## Command usage

```text
/memory-audit
/memory-audit status
/memory-audit run
```

## Local CLI usage

```bash
python3 src/audit.py --dir memory --out report.md --json report.json
```

## Demo

```bash
bash demo/run_demo.sh
```

## License

MIT


## v0.2 additions

- Configurable score weights via `audit.config.json`
- Ignore rules (`ignore_patterns`)
- Multi-folder scan (`memory/**/*.md`) + optional `MEMORY.md`
- Remediation suggestions in markdown report


## v0.3 additions

- `/memory-audit config-check`
- strict mode: `python3 src/audit.py run --strict ...`
- CI memory quality gate workflow
