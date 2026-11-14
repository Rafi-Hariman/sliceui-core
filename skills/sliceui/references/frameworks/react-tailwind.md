# Framework Guide — React + Tailwind CSS

## Component Conventions

- One component per file: `src/components/<Name>.tsx`.
- Function components with typed props (`interface <Name>Props`).
- PascalCase component names, `camelCase` props.
- Named exports for shared components; default export for page components.

## Props / Slots / Children Mapping

| FigML node | React mapping |
|---|---|
| `<Button_FNC>` | `<button className="...">{label}</button>` with `onClick` prop |
| `<Field_FNC>` | `<input>` / `<select>` with `value` + `onChange` (controlled) |
| `<Tab_basic>` | `<button role="tab" aria-selected={active}>` |
| `<Card>` | `<div className="rounded-... border ...">` wrapping children |
| repeated text/rows | `children` or a `data` array mapped with `.map()` |

## Styling Tokens (Tailwind)

Read values from the XML and emit Tailwind utilities:

- `fill color="#hex"` → `bg-[#hex]` or a `theme` token when the repo defines one.
- `fontSize` → `text-[<N>px]` / `text-sm|base|lg`.
- `cornerRadius` → `rounded-[<N>px]` / `rounded-lg`.
- `itemSpacing` → `gap-[<N>px]`.
- `layoutMode` → `flex flex-row` / `flex flex-col`.
- opacity → `/opacity` modifier (`bg-blue-500/80`).

Prefer existing `tailwind.config` theme tokens when the repo has them; fall back
to arbitrary values `[...]` otherwise.

## Chart Integration

- Recharts is the default when already installed; otherwise render inline SVG.
- Donut/pie: compute each slice path with `sliceui.py arc`, feed into
  `<PieChart>`/`<Pie>` or a raw `<path>` inside `<svg viewBox>`.
- Bar/line: map the exact per-category rectangle/vector counts from the XML to
  series data — never assume equal bar counts across categories.
