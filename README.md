# sliceui

High-precision, context-efficient **Figma XML (`.figml`) UI slicing skill and
CLI engine for Claude Code**. A zero-dependency Node.js installer pairs with a
deterministic Python `lxml` engine so Claude can slice a `.figml` export into
accurate UI code — without hallucinating text, numbers, or colors.

## Architecture (2-space install)

- **`bin/cli.js`** — Node.js (>=18) CLI. Installs the skill to either the global
  (`~/.claude/skills/sliceui`) or project (`.claude/skills/sliceui`) space, and
  bootstraps an isolated Python `.venv` with `lxml` (PEP 668 safe).
- **`skills/sliceui/`** — the Claude Code skill itself:
  - `SKILL.md` — orchestrator (routing + anti-hallucination protocol).
  - `scripts/sliceui.py` — deterministic XML engine (`compact`, `outline`,
    `cut`, `arc`, `verify`).
  - `references/` — domain rules and framework guides.

## Installation

```bash
# Install the skill for all projects
npx sliceui init --global

# Install the skill into the current project only
npx sliceui init --project

# Scaffold a project context file (overrides skill defaults for this repo)
npx sliceui init --context --force

# Verify / repair the Python + lxml environment
npx sliceui doctor --target ~/.claude/skills/sliceui
```

`init` automatically runs `doctor`, which finds `python3`/`python`, checks for
`lxml`, and if it is missing creates `<skill_dir>/.venv` and installs `lxml`
there — avoiding PEP 668 `externally-managed-environment` errors.

## Using the skill in Claude Code

**Standalone mode (Phase 1)** — slice a `.figml` into standalone
HTML/CSS/Bootstrap:

> Slice `dashboard.figml` into `dashboard.html` and `dashboard.css` (standalone
> Bootstrap 5 + Font Awesome).

**Codebase mode (Phase 2)** — slice into an existing project:

> Slice `dashboard.figml` into my Angular/Tailwind app, matching the existing
> `Button`, `Card`, and chart components.

The skill automatically runs `compact` → `outline` → per-section `cut` → writes
output files → `verify`, and self-repairs until text coverage is 100%.

## `sliceui.py` CLI reference

```bash
python3 <skill_dir>/scripts/sliceui.py compact <input.figml> [--out out.xml]
python3 <skill_dir>/scripts/sliceui.py outline <compact.xml>
python3 <skill_dir>/scripts/sliceui.py cut <compact.xml> --id <id> [--id <id2> ...]
python3 <skill_dir>/scripts/sliceui.py arc --width <W> --height <H> --start <rad> --end <rad> [--inner <ratio>]
python3 <skill_dir>/scripts/sliceui.py verify <compact.xml> <out1.html> [<out2.css> ...]
```

| Command | Purpose |
|---|---|
| `compact` | Lossless compression — strips Figma metadata, normalizes numbers, collapses hidden nodes, dedups repeated decorative patterns. |
| `outline` | Structural map with auto flags: `IMAGE`, `ARC_CHART`, `VECTOR_CURVE`, `REPEATED(xN)`, `HIDDEN`. |
| `cut` | Extract one or more node subtrees by id, with parent-context header comments. |
| `arc` | Convert Figma `arcData` angles into a precise SVG `<path d="..."/>`. |
| `verify` | Audit text + color coverage across generated files (exit 0 at 100% text, exit 2 otherwise). |

## License

MIT
