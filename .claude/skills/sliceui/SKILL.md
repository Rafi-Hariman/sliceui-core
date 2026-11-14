---
name: sliceui
description: >-
  Slice a Figma XML (.figml) export into accurate, token-efficient UI code.
  Use when the user asks to convert/slice a .figml or Figma design into
  HTML/CSS/Bootstrap (standalone) or into an existing codebase/framework.
  Deterministic pipeline: prep -> read -> write -> verify. Never guesses text,
  numbers, or colors — every value is read from the XML.
---

# SliceUI — Figma XML (.figml) → UI Code

Deterministic, anti-hallucination slicing. Every text, number, and color is
read from the XML — never invented.

## Context Priority

If `./.claude/skills/sliceui/project-context.md` exists in the workspace, its
conventions override everything below. Otherwise use the active mode defaults.

## Mode Routing

- **Standalone (default):** slicing into standalone HTML/CSS/Bootstrap, no
  existing project → read `references/core-rules.md` + `references/mode-standalone.md`.
- **Codebase:** integration into an existing project/framework → read
  `references/mode-codebase.md` + the matching `references/frameworks/<f>.md`.

## Execution Protocol

Do NOT read the source code of `sliceui.py` — just run it:

```
step 1  READ REFERENCES — in ONE turn, read core-rules.md + the active mode
        file in parallel.
step 2  PREP
        python3 <skill_dir>/scripts/sliceui.py prep <file.figml>
step 3  READ RESULT
        if prep output < 1200 lines -> read the whole file in ONE Read.
        else -> outline then cut per section (top -> bottom, no skipping).
step 4  WRITE + VERIFY
        after reading prep, write .css, .html, and .js in PARALLEL — three
        Write calls in ONE turn, no re-analysis between them. Then run
        python3 <skill_dir>/scripts/sliceui.py verify <prep.xml> <outputs...>
        and fix hard-gate failures until exit 0.
```

## Verify Hard Gates (must all pass — exit 2 on failure)

1. **100% text** — every visible `characters` value appears in the output.
2. **Zero Bootstrap class conflict** — no unprefixed `tooltip`, `placeholder`,
   `card-header`, `badge`, or `toast` (Bootstrap's own `toast` is allowed only
   as `class="toast sui-toast"`).
3. **All `.sui-*` classes defined** — every `sui-*` class used in the HTML has
   a matching `.sui-*` rule in the CSS (checked HTML → CSS, not the reverse).

`<skill_dir>` is the directory containing this SKILL.md.
