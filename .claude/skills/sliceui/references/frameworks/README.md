# Framework Knowledge Guides

Each file in this folder teaches the skill how to slice a `.figml` into a
specific framework's idiom. The skill loads the matching file automatically in
Codebase mode (`references/mode-codebase.md`).

## How to Add a New Framework Guide

Create a new file named `<framework>.md` (e.g. `vue-tailwind.md`,
`nextjs-shadcn.md`) and cover, in order:

1. **Component conventions** — file naming, export style, folder layout.
2. **Props / slots / children mapping** — how FigML nodes map to component
   props, slots, or children.
3. **Styling tokens** — how colors, typography, spacing, and radius from the
   XML map to the framework's styling system (Tailwind classes, CSS modules,
   styled-components, etc.).
4. **Chart integration** — which chart library to use and how to feed it the
   slice geometry from `arc` / bar / line rules.

Keep each guide concrete and copy-ready. The skill reads it verbatim before
generating code in Codebase mode.
