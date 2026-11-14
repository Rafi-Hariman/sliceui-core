# Mode Codebase — Phase 2 (Integration)

Active when the user wants the `.figml` sliced into an existing project or
framework. Always adapt to the repo's idiom rather than imposing defaults.

## Workflow

1. **Read project context** — `.claude/skills/sliceui/project-context.md`
   (if present). Its conventions win.
2. **Inspect the repo** — read `package.json` / `composer.json`, and 2–3
   existing UI components to match naming, styling, and reusable components
   (`Button`, `Input`, `Tabs`, `Card`, and the chart library if installed).
3. **Load the framework guide** — `references/frameworks/<framework>.md` that
   matches the repo.
4. **Map before you create** — map each `.figml` element to an existing project
   component first; only create a new component when no equivalent exists.
   Reuse props/slots/classes per the framework guide.
5. **Verify** — run
   `python3 <skill_dir>/scripts/sliceui.py verify <compact.xml> <generated files...>`
   against every generated component file and repair until text coverage is
   100%.

## Rules

- Match the repo's existing conventions (naming, styling, tokens) — do not
  import Bootstrap/Font Awesome unless the repo already uses them.
- Keep edits scoped to the authorized target files the user names.
