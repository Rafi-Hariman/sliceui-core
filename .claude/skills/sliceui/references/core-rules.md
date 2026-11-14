# Core Rules — prep attribute translation, layout & charts

The `prep` output is a flat, attribute-rich XML. Translate these attributes
literally — never reinterpret values.

## 1. prep attribute → CSS/HTML

### Layout
| prep attribute | output |
|---|---|
| `layoutMode="HORIZONTAL"` | `display:flex; flex-direction:row;` |
| `layoutMode="VERTICAL"` | `display:flex; flex-direction:column;` |
| `primaryAxisAlignItems="MIN/CENTER/MAX/SPACE_BETWEEN"` | `justify-content:flex-start/center/flex-end/space-between;` |
| `counterAxisAlignItems="MIN/CENTER/MAX/BASELINE"` | `align-items:flex-start/center/flex-end/baseline;` |
| `layoutWrap="WRAP"` | `flex-wrap:wrap;` |
| `itemSpacing="N"` | `gap:Npx;` |
| `paddingLeft/Right/Top/Bottom` | `padding:T R B L;` (px) |
| `layoutSizingHorizontal="FILL"` / `layoutGrow="1"` | `flex:1 1 0%; width:100%;` |
| `layoutPositioning="ABSOLUTE"` | `position:absolute; left:x; top:y;` (parent `position:relative`) |
| `clipsContent="true"` | `overflow:hidden;` |

### Visual
| prep attribute | output |
|---|---|
| `fill="#hex"` | `background:#hex;` |
| `fill="#hex@op"` | `background:rgba(hex, op);` |
| `fill="IMAGE"` | layered avatar/media placeholder SVG (never blank) |
| `fill="gradient(0:#a,1:#b)"` | `background:linear-gradient(#a,#b);` |
| `fill="A \| B"` | multiple fills → top-most last (or layered backgrounds) |
| `stroke="#hex:w"` | `border:w px solid #hex;` |
| `stroke="#hex:w:dashed"` | `border:w px dashed #hex;` |
| `shadow="x,y,r,#hex[@op]"` | `box-shadow:x y r rgba(hex, op)` (default `op=.15` if absent) |
| `cornerRadius="N"` | `border-radius:N px;` |
| `svgPath="M..."` | use directly as `<path d="M..."/>` (donut/pie); full-circle → `<circle>` |

### Text
- `font="Family:Style:size[/lineHeight][@letterSpacing]"`:
  `font-family:Family; font-size:size px; line-height:lineHeight (or 1.4 if AUTO);
  letter-spacing:@px`. `Style` → weight: `Bold→700, SemiBold→600, Medium→500,
  Regular→400, Light→300, ExtraBold→800`; `Symbol(figma.mixed)` → use `fontWeight`.
- `characters`: ` ` → `<br>` in tooltips, plain space in paragraphs.

## 2. Desktop + responsive alignment (anti-regression)

- Vertical multi-section wrapper `.sui-content { display:flex; flex-direction:column; gap:16px; }`.
- Companion columns inside Bootstrap `.row` use `.sui-side-col { height:100%; }`
  so left/right cards stay equal-height on desktop.
- A text block beside a fixed-size media/chart (e.g. `.sui-donut-stats` beside a
  191px Donut) in a `flex-wrap:wrap` row gets `flex:1 1 220px; min-width:0;`
  — horizontal on desktop, wraps only below `480px`.
- Full-banner decorative `<svg>` gets `width="100%" height="100%"`, and the
  gradient background element is drawn BEFORE any transparent (`opacity<1`)
  pattern element so the pattern is never covered.
- When a row whose children use `flex:1 1 0%` becomes `flex-direction:column` at
  `<=575.98px`, reset children to `align-items:stretch; flex:none; width:100%;`.

## 3. Charts, grid & tooltips

### Donut / Pie
- Use `svgPath` from `prep` directly inside `<svg viewBox="0 0 W H">`. Center
  label via `position:absolute; inset:0; display:flex; center`.

### Bar chart
- Per-chart bar `width` + `gap` from each `<Rectangle>` width / column pitch —
  never share one width across charts with different column counts.
- Render dashed horizontal grid lines equal to the Y-label tick count.

### Line chart
- Horizontal grid, X/Y axes, tick marks, dashed threshold aligned to its own
  Y-label value, a `<circle>` node per month, and
  `<!-- TODO: bind dynamic line series data -->`.

### Scroll & static tooltip (anti-overflow)
- Charts with `>= 5` columns wrap in
  `.sui-chart-scroll { overflow-x:auto; padding-top:40px; }` with inner
  `min-width:680px` (11–12 months) or `520px` (5 semesters) so the chart pans
  instead of collapsing on a 360px phone.
- Static tooltips use `top:-30px` and are placed exactly above the column
  matching their label text.

## 4. v2.1 refinements (mandatory)

1. **Line chart completeness** — always render an `<svg>` containing a
   `<polyline>` trend curve and a `<circle>` node for every X-axis label, with
   `<!-- TODO: bind dynamic line series data -->` placed **above** the `<svg>`.
   Never leave the line plot area blank.
2. **Banner + stacked right column** — the top card (banner) is `flex: none;`
   and the bottom card (`.sui-ipkeg`) is `flex: 1 1 auto;` — do NOT use
   `height: 100%` on the bottom card (it clips the banner above it). Render the
   banner circle pattern as an `<svg><pattern>` with `opacity="0.28"` layered
   above the gradient, without `mix-blend-mode: multiply`.
3. **Filter dropdown** — the filter field container (`FILL`) must not be capped
   at `max-width: 300px` on desktop; use a semantic
   `<select class="form-select sui-select">`.
4. **Bar chart & avatar** — bars use `border-radius: 8px 8px 0 0` (flat bottom);
   per-chart bar width (`25px` for 11-month, `35px` for 5-semester); each static
   tooltip sits on the column matching its label; `fill="IMAGE"` renders a
   layered `<svg>` silhouette (`146×184`).
5. **Toast hidden on load** — always use Bootstrap's `toast` class
   (`class="toast sui-toast"`) so it is hidden at page load and only appears
   after the action button is clicked.

## 5. Final polish (mandatory)

- **Page background** — use the `fill` of the top-level `<Frame>` as the
  `body` `background` (fall back to `#ffffff` when the frame has no fill). Do
  NOT add an artificial gray canvas (e.g. `#eef1f7`) outside the main frame.
- **Mobile avatar & filters (≤ 575.98px)** — keep the avatar at its original
  `width: 146px; height: 184px; align-self: center;` (never stretch it to
  `width: 100%`). `.sui-filters` becomes `flex-direction: column;
  align-items: stretch;` with every child `flex: none; width: 100%;`.
