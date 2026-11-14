# Framework Guide — Laravel + Blade

## Component Conventions

- Views live in `resources/views/`; partials in `resources/views/partials/`.
- Prefer Blade components (`<x-...>`) when the repo uses them; otherwise
  `@include('partials.<name>')`.
- `kebab-case` view filenames, snake_case data keys.
- Blade templates: `{{ $var }}` (escaped), `{!! $html !!}` (raw, sparingly).

## Props / Slots / Children Mapping

| FigML node | Blade mapping |
|---|---|
| `<Button_FNC>` | `<button class="btn ...">{{ $label }}</button>` or `<x-button>` |
| `<Field_FNC>` | `<select class="form-select">` with `@foreach` options |
| `<Tab_basic>` | `<button role="tab" class="nav-link ...">` |
| `<Card>` | `<div class="card"><div class="card-body">@yield/slot` |
| repeated rows | `@foreach ($items as $item)` loop over a `$data` collection |

## Styling Tokens

- Use the repo's existing CSS framework (Bootstrap by default for Laravel).
- Colors/typography/spacing from the XML map to CSS variables or existing
  utility classes; define `:root` tokens in `resources/css/app.css` if absent.
- `layoutMode` → `d-flex flex-row` / `d-flex flex-column`; `itemSpacing` →
  `gap-<N>` (Bootstrap 5.3) or inline `style="gap: <N>px"`.

## Chart Integration

- Chart.js is the default if installed; otherwise inline SVG in the Blade view.
- Donut/pie: compute slice paths via `sliceui.py arc` and pass into Chart.js
  datasets or render raw `<path>` inside `<svg viewBox>`.
- Bar/line: derive per-category series data from the exact XML counts — never
  assume equal bar counts across categories.
- Keep chart data in a controller-assigned variable (`$chartData`) so the view
  stays declarative.
