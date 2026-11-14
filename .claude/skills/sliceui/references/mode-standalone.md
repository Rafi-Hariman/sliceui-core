# Mode Standalone — Phase 1 (Separated Output)

Active when slicing a `.figml` into standalone HTML/CSS/Bootstrap with no
existing project. Read `core-rules.md` first.

## Output: 3 compact files

Produce exactly 3 files in the requested directory (or cwd), kept lean:

1. `<nama>.css` — written first. Target **240–340 lines**, no duplicate
   declarations. Define the full `:root` palette (colors + `--font`).
2. `<nama>.html` — written second. Target **260–360 lines**. Loads CSS via
   `<link>`. For a second tab panel (e.g. `Tabel`), render a compact summary
   table — do NOT duplicate hundreds of lines.
3. `<nama>.js` — written third, `< 90 lines`. Only: tab switching, Bootstrap
   tooltips on `(i)` icons, hover tooltips for bars/nodes, and the action
   button toast. Load via `<script src="./<nama>.js">` after the Bootstrap
   bundle. No inline `<script>` in HTML.

## Stack

- Bootstrap 5.3 CSS+JS bundle via CDN; Font Awesome 6 (if icons); Google Fonts
  for every font family in the XML.

## Namespace `.sui-*` (mandatory)

- Prefix EVERY custom class with `sui-`: `.sui-card`, `.sui-card-head`,
  `.sui-tooltip`, `.sui-badge`, `.sui-toast`, `.sui-select`, `.sui-table`, etc.
- Forbidden unprefixed: `tooltip`, `placeholder`, `card-header`, `badge`,
  `toast` (and other Bootstrap component names). Bootstrap grid/utilities
  (`row`, `col-lg-*`, `d-flex`, `g-3`) are allowed.
- `verify` fails (exit 2) on: missing text, unprefixed Bootstrap class,
  undefined `.sui-*` class, or missing viewport/breakpoints.

## Quality

- `:root` custom properties for the full palette from the XML; Bootstrap grid
  for macro layout, precise Flex/Grid inside cards; opens via `file://` with no
  build step; responsive at 991.98px / 575.98px per `core-rules.md`.
