# CLAUDE.md — `sliceui` NPM Package & Claude Code Skill

## Project Purpose & Architecture
`sliceui` is a zero-dependency Node.js CLI installer paired with a deterministic Python `lxml` engine that enables Claude Code to slice Figma XML (`.figml`) exports into accurate, token-efficient UI code.

- `bin/cli.js`: Node.js (`>=18`) CLI managing 2-space installation (`--global` -> `~/.claude/skills/sliceui`, `--project` -> `./.claude/skills/sliceui`), project context scaffolding (`--context`), and isolated Python `.venv` setup (`doctor`).
- `skills/sliceui/SKILL.md`: Main skill orchestrator (must stay **under 180 lines**). Routes between Standalone mode (Phase 1) and Codebase mode (Phase 2).
- `skills/sliceui/scripts/sliceui.py`: Deterministic XML processor (`compact`, `outline`, `cut`, `arc`, `verify`).
- `skills/sliceui/references/`: Modular domain rules (`figml-schema-rules.md`, `charts-and-assets.md`, `mode-standalone.md`, `mode-codebase.md`, and `frameworks/*.md`).

For initial build specifications, refer to `@sliceui-master-prompt.md`.

## Mandatory Verification Commands
After ANY change to `bin/cli.js`, `skills/sliceui/scripts/sliceui.py`, or skill files, run and pass all checks before concluding:

```bash
chmod +x bin/cli.js skills/sliceui/scripts/sliceui.py
node --check bin/cli.js
python3 -m py_compile skills/sliceui/scripts/sliceui.py
node ./bin/cli.js --help
python3 skills/sliceui/scripts/sliceui.py --help
python3 skills/sliceui/scripts/sliceui.py arc --width 191 --height 191 --start 4.7124 --end 9.5497 --inner 0.5265