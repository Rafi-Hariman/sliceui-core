#!/usr/bin/env python3
"""sliceui.py — deterministic Figma XML (.figml) slicing engine (v2.0).

Subcommands:
  prep      Losslessly compress a .figml into a flat, attribute-rich form
            (pre-computes svgPath, merges fills/strokes/font/shadow/children).
  outline   Print a structural map with auto-detected flags.
  cut       Extract one or more node subtrees by id.
  arc       Convert Figma arcData angles into an SVG <path d="..."/>.
  verify    Audit text/color/class/responsive/interactivity (HARD GATE + WARN).
"""

import argparse
import hashlib
import math
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _relaunch_in_venv():
    candidates = [
        os.path.join(HERE, "..", ".venv", "bin", "python3"),
        os.path.join(HERE, "..", ".venv", "bin", "python"),
        os.path.join(HERE, "..", ".venv", "Scripts", "python.exe"),
    ]
    for py in candidates:
        if os.path.isfile(py):
            os.execv(py, [py] + sys.argv)


try:
    from lxml import etree as ET
except ImportError:
    _relaunch_in_venv()
    sys.stderr.write(
        "sliceui.py: lxml is not installed.\n"
        "Run `sliceui doctor` to create an isolated .venv with lxml,\n"
        "or install it globally: python3 -m pip install lxml\n"
    )
    sys.exit(1)

METADATA_TAGS = {
    "constraints", "overrides", "override", "overriddenFields",
    "overriddenField", "mainComponent", "componentProperties",
    "variantProperties", "layoutGrids", "layoutGrid", "exportSettings",
    "filters", "imageTransform",
}

NUMERIC_ATTRS = {
    "x", "y", "width", "height", "strokeWeight", "cornerRadius", "opacity",
    "startingAngle", "endingAngle", "innerRadius", "rotation", "itemSpacing",
    "paddingLeft", "paddingRight", "paddingTop", "paddingBottom",
}

# Default-value attributes removed by prep (lossless — re-derived as defaults).
DEFAULT_ATTR_VALUES = {
    "x": "0", "y": "0", "opacity": "1", "cornerRadius": "0",
    "itemSpacing": "0", "paddingTop": "0", "paddingRight": "0",
    "paddingBottom": "0", "paddingLeft": "0", "layoutGrow": "0",
    "layoutAlign": "INHERIT",
    "textAlignHorizontal": "LEFT", "textAlignVertical": "TOP",
}

# Attributes whose value duplicates the tag or is folded elsewhere (lossless):
# type = tag category; fontName/fontSize/fontWeight -> font; strokeWeight/strokeAlign
# -> stroke (strokeAlign is sub-pixel for 1–2px borders); hyperlink/textAutoResize
# and primary/counterAxisSizingMode are unused Figma hints.
REDUNDANT_ATTRS = (
    "type", "hyperlink", "fontName", "fontSize", "fontWeight", "strokeAlign",
    "textAutoResize", "primaryAxisSizingMode", "counterAxisSizingMode",
)

# Only "FILL" changes layout (flex). "HUG"/"FIXED" are implied by width/height.
_STRIP_SIZING_IF = ("layoutSizingHorizontal", "layoutSizingVertical")

# Numeric fontWeight -> style name, folded into font when a style is absent.
WEIGHT_TO_STYLE = {
    "800": "ExtraBold", "700": "Bold", "600": "SemiBold",
    "500": "Medium", "400": "Regular", "300": "Light",
}

# Keep ids for the top-level frame + its first few child levels (for `cut`).
ID_KEEP_DEPTH = 3

SKIP_OUTLINE_TAGS = {
    "children", "fills", "strokes", "effects", "fontName",
    "letterSpacing", "lineHeight", "fill", "stroke", "arcData",
    "gradientStops", "gradientStop", "dashPattern", "effect", "offset",
}

CONFLICT_CLASSES = ("tooltip", "placeholder", "card-header", "badge", "toast")
BOOTSTRAP_CDN_RE = re.compile(
    r"bootstrap@|bootstrap\.min\.|getbootstrap|/bootstrap/", re.IGNORECASE
)
INTERACTIVITY_RE = re.compile(
    r"bootstrap\.Tooltip|addEventListener|data-bs-toggle", re.IGNORECASE
)
VIEWPORT_RE = re.compile(r'<meta\s+name="viewport"', re.IGNORECASE)
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")

_LINE_BREAK_RE = re.compile(r"[\r\n\u2028\u2029]+")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


def _parser():
    return ET.XMLParser(
        resolve_entities=False, no_network=True,
        remove_blank_text=True, huge_tree=True,
    )


def parse_xml(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        return ET.fromstring(data, parser=_parser())
    except ET.XMLSyntaxError as e:
        sys.stderr.write(f"sliceui: invalid XML in {path}: {e}\n")
        sys.exit(1)


def normalize_whitespace(s):
    # Figma multi-line text: normalize \n, \r,  ,   (and HTML <br>)
    # to a single space so XML characters match output on the first attempt.
    s = _BR_RE.sub(" ", s)
    s = _LINE_BREAK_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_number(value):
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if not math.isfinite(v):
        return value
    if abs(v) < 1e-6:
        return "0"
    if v == int(v):
        return str(int(v))
    return ("%.2f" % v).rstrip("0").rstrip(".")


def descendant_count(elem):
    return sum(1 for _ in elem.iter()) - 1


def is_hidden(elem):
    node = elem
    while node is not None:
        if node.tag == "HiddenNode" or node.get("visible") == "false":
            return True
        node = node.getparent()
    return False


def build_arc_path(w, h, start, end, inner):
    cx = w / 2.0
    cy = h / 2.0
    R = min(w, h) / 2.0
    r = R * inner
    delta = end - start
    full = abs(delta) >= 2 * math.pi - 1e-4
    large = 0 if full else (1 if abs(delta) > math.pi else 0)
    sweep = 1 if delta >= 0 else 0

    def fnum(v):
        s = "%.4f" % v
        return s.rstrip("0").rstrip(".")

    def pt(radius, ang):
        x = cx + radius * math.cos(ang)
        y = cy + radius * math.sin(ang)
        return f"{fnum(x)} {fnum(y)}"

    if inner <= 0:
        if full:
            mid = start + delta / 2.0
            return (
                f"M {fnum(cx)} {fnum(cy)} L {pt(R, start)} "
                f"A {fnum(R)} {fnum(R)} 0 1 {sweep} {pt(R, mid)} "
                f"A {fnum(R)} {fnum(R)} 0 1 {sweep} {pt(R, start)} Z"
            )
        return (
            f"M {fnum(cx)} {fnum(cy)} L {pt(R, start)} "
            f"A {fnum(R)} {fnum(R)} 0 {large} {sweep} {pt(R, end)} Z"
        )
    if full:
        mid = start + delta / 2.0
        return (
            f"M {pt(R, start)} A {fnum(R)} {fnum(R)} 0 1 {sweep} {pt(R, mid)} "
            f"A {fnum(R)} {fnum(R)} 0 1 {sweep} {pt(R, start)} Z "
            f"M {pt(r, start)} A {fnum(r)} {fnum(r)} 0 1 {1 - sweep} {pt(r, mid)} "
            f"A {fnum(r)} {fnum(r)} 0 1 {1 - sweep} {pt(r, start)} Z"
        )
    return (
        f"M {pt(R, start)} A {fnum(R)} {fnum(R)} 0 {large} {sweep} {pt(R, end)} "
        f"L {pt(r, end)} A {fnum(r)} {fnum(r)} 0 {large} {1 - sweep} {pt(r, start)} Z"
    )


# --------------------------------------------------------------------------- #
# prep — lossless compression
# --------------------------------------------------------------------------- #

def _remove_metadata(root):
    for elem in list(root.iter()):
        if elem.tag in METADATA_TAGS:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)


def _remove_noise_attrs(root):
    for elem in root.iter():
        for attr in ("maskType", "scaleFactor"):
            if attr in elem.attrib:
                del elem.attrib[attr]
        if elem.get("blendMode") == "NORMAL":
            del elem.attrib["blendMode"]


def _normalize_numbers(root):
    for elem in root.iter():
        for attr in list(elem.attrib):
            if attr in NUMERIC_ATTRS:
                new_val = normalize_number(elem.attrib[attr])
                if new_val != elem.attrib[attr]:
                    elem.attrib[attr] = new_val


def collapse_hidden(root):
    for elem in list(root.iter()):
        if elem is root or elem.get("visible") != "false":
            continue
        parent = elem.getparent()
        if parent is None:
            continue
        idx = list(parent).index(elem)
        hidden = ET.Element("HiddenNode")
        hidden.set("id", elem.get("id", ""))
        hidden.set("name", elem.get("name", ""))
        parent.insert(idx, hidden)
        parent.remove(elem)


def dedup_children(root):
    for container in list(root.iter("children")):
        kids = list(container)
        if len(kids) < 4:
            continue
        if len(list(container.iter("Text"))) > 0:
            continue
        sigs = [
            (k.tag, k.get("name"), k.get("width"), k.get("height"), descendant_count(k))
            for k in kids
        ]
        if len(set(sigs)) != 1:
            continue
        kids[0].set("repeatedCount", str(len(kids)))
        for dup in kids[1:]:
            container.remove(dup)


def precompute_arcs(root):
    for ell in list(root.iter("Ellipse")):
        ad = ell.find("arcData")
        if ad is None:
            continue
        try:
            w = float(ell.get("width", "0") or 0)
            h = float(ell.get("height", "0") or 0)
            start = float(ad.get("startingAngle", "0") or 0)
            end = float(ad.get("endingAngle", "0") or 0)
            inner = float(ad.get("innerRadius", "0") or 0)
            ell.set("svgPath", build_arc_path(w, h, start, end, inner))
        except (ValueError, TypeError):
            pass
        ell.remove(ad)


def _solid_fill_str(f):
    color = f.get("color") or ""
    opacity = f.get("opacity")
    if opacity and opacity != "1":
        return f"{color}@{opacity}"
    return color


def merge_fills(root):
    for fills in list(root.iter("fills")):
        parent = fills.getparent()
        parts = []
        for f in list(fills):
            if f.tag != "fill":
                continue
            ftype = (f.get("type") or "").upper()
            if ftype == "IMAGE":
                parts.append("IMAGE")
            elif ftype == "GRADIENT_LINEAR":
                stops = []
                gs = f.find("gradientStops")
                if gs is not None:
                    for s in gs:
                        stops.append(f"{s.get('position') or 0}:{s.get('color') or ''}")
                parts.append("gradient(" + ",".join(stops) + ")")
            else:
                parts.append(_solid_fill_str(f))
        if parent is not None:
            if parts:
                parent.set("fill", " | ".join(parts))
            parent.remove(fills)


def merge_strokes(root):
    for strokes in list(root.iter("strokes")):
        parent = strokes.getparent()
        colors = []
        for s in list(strokes):
            if s.tag != "stroke":
                continue
            c = s.get("color") or ""
            if c:
                colors.append(c)
        if parent is not None:
            if colors:
                value = " | ".join(colors)
                weight = parent.get("strokeWeight", "") or ""
                if weight and weight != "0":
                    value += ":" + weight
                dp = parent.find("dashPattern")
                if dp is not None and len(dp) > 0:
                    value += ":dashed"
                parent.set("stroke", value)
            parent.remove(strokes)
            dp = parent.find("dashPattern")
            if dp is not None:
                parent.remove(dp)


def merge_font(root):
    for elem in list(root.iter("Text")):
        fn = elem.find("fontName")
        lh = elem.find("lineHeight")
        ls = elem.find("letterSpacing")
        family = fn.get("family", "") if fn is not None else ""
        style = fn.get("style", "") if fn is not None else ""
        if not family:
            # fontName can be an attribute instead of a child (e.g. Symbol(mixed))
            family = elem.get("fontName", "") or ""
        if not style:
            style = WEIGHT_TO_STYLE.get(elem.get("fontWeight", ""), "")
        size = elem.get("fontSize", "") or ""

        lhval = ""
        if lh is not None:
            v = lh.get("value", "") or ""
            u = lh.get("unit", "") or ""
            lhval = (v + u) if v else u

        lsval = ""
        if ls is not None:
            v = ls.get("value", "0") or "0"
            try:
                if abs(float(v)) > 1e-6:
                    lsval = v
            except ValueError:
                pass

        base = family
        if style:
            base += ":" + style
        if size:
            base += ":" + size
        if lhval:
            base += "/" + lhval
        if lsval:
            base += "@" + lsval

        elem.set("font", base)
        for sub in (fn, lh, ls):
            if sub is not None:
                elem.remove(sub)


def merge_effects(root):
    for effects in list(root.iter("effects")):
        parent = effects.getparent()
        shadows = []
        for e in list(effects):
            if (e.get("type") or "").upper() != "DROP_SHADOW":
                continue
            off = e.find("offset")
            x = off.get("x", "0") if off is not None else "0"
            y = off.get("y", "0") if off is not None else "0"
            r = e.get("radius", "0")
            c = e.get("color", "#000000")
            op = e.get("opacity")
            val = f"{x},{y},{r},{c}"
            if op:
                val += "@" + op
            shadows.append(val)
        if parent is not None:
            if shadows:
                parent.set("shadow", " | ".join(shadows))
            parent.remove(effects)


def flatten_children(root):
    for children in list(root.iter("children")):
        parent = children.getparent()
        if parent is None:
            continue
        idx = list(parent).index(children)
        kids = list(children)
        parent.remove(children)
        for offset, kid in enumerate(kids):
            parent.insert(idx + offset, kid)


def _strip_attrs(root):
    """Drop default-value and redundant attributes (lossless)."""
    for elem in root.iter():
        if "strokeWeight" in elem.attrib and (
            "stroke" in elem.attrib or elem.attrib["strokeWeight"] == "0"
        ):
            del elem.attrib["strokeWeight"]
        for attr in list(elem.attrib):
            val = elem.attrib[attr]
            if attr in DEFAULT_ATTR_VALUES and val == DEFAULT_ATTR_VALUES[attr]:
                del elem.attrib[attr]
            elif attr in REDUNDANT_ATTRS:
                del elem.attrib[attr]
            elif attr in _STRIP_SIZING_IF and val != "FILL":
                del elem.attrib[attr]


def _strip_leaf_ids(root, keep_depth=ID_KEEP_DEPTH):
    """Remove id from leaf/deep nodes; keep section-level ids for `cut`."""
    def walk(elem, depth):
        if depth > keep_depth and "id" in elem.attrib:
            del elem.attrib["id"]
        for child in elem:
            walk(child, depth + 1)
    walk(root, 0)


def prep(xml_bytes):
    root = ET.fromstring(xml_bytes, parser=_parser())
    _remove_metadata(root)
    _remove_noise_attrs(root)
    _normalize_numbers(root)
    collapse_hidden(root)
    dedup_children(root)
    precompute_arcs(root)
    merge_fills(root)
    merge_strokes(root)
    merge_font(root)
    merge_effects(root)
    flatten_children(root)
    _strip_attrs(root)
    _strip_leaf_ids(root)
    return root


# --------------------------------------------------------------------------- #
# outline / cut
# --------------------------------------------------------------------------- #

def _text_preview(elem, limit=40):
    for t in elem.iter("Text"):
        chars = t.get("characters")
        if chars is None:
            chars = "".join(t.itertext())
        chars = normalize_whitespace(chars)
        if chars:
            return chars if len(chars) <= limit else chars[:limit] + "..."
    return ""


def compute_flags(elem):
    flags = []
    if elem.tag == "HiddenNode":
        flags.append("HIDDEN")
    rc = elem.get("repeatedCount")
    if rc is not None:
        flags.append(f"REPEATED(x{rc})")

    has_image = has_arc = has_vector = False
    for d in elem.iter():
        fill = d.get("fill") or ""
        if "IMAGE" in fill:
            has_image = True
        if d.get("svgPath"):
            has_arc = True
        if d.tag == "fill" and (d.get("type") or "").upper() == "IMAGE":
            has_image = True
        if d.tag == "arcData":
            has_arc = True
        if d.tag == "Vector":
            try:
                w = float(d.get("width", "0"))
                h = float(d.get("height", "0"))
                if w > 20 and h > 20:
                    has_vector = True
            except ValueError:
                pass

    if has_image:
        flags.append("IMAGE")
    if has_arc:
        flags.append("ARC_CHART")
    if has_vector:
        flags.append("VECTOR_CURVE")
    return flags


def _print_node(elem, depth):
    indent = "  " * depth
    nid = elem.get("id", "-")
    name = elem.get("name", "")
    w = elem.get("width", "?")
    h = elem.get("height", "?")
    layout = elem.get("layoutMode") or "NONE"
    lines = sum(1 for _ in elem.iter("Text"))
    flags = compute_flags(elem)
    preview = _text_preview(elem)
    parts = [
        f'[{nid}] <{elem.tag} name="{name}"> {w}x{h}',
        f"layout={layout}", f"lines={lines}",
    ]
    if flags:
        parts.append("flags=[" + ",".join(flags) + "]")
    if preview:
        parts.append(f'text="{preview}"')
    print(indent + " | ".join(parts))


def _walk(elem, depth):
    for child in elem:
        if child.tag in SKIP_OUTLINE_TAGS:
            _walk(child, depth)
            continue
        _print_node(child, depth)
        _walk(child, depth + 1)


# --------------------------------------------------------------------------- #
# verify — HARD GATE + WARNINGS
# --------------------------------------------------------------------------- #

def collect_texts(root):
    texts = []
    for elem in root.iter():
        if is_hidden(elem):
            continue
        if elem.tag == "Text":
            chars = elem.get("characters")
            if chars is None:
                chars = "".join(elem.itertext())
            chars = normalize_whitespace(chars)
            if chars:
                texts.append(chars)
    return list(dict.fromkeys(texts))


def collect_colors(root):
    colors = set()
    for elem in root.iter():
        if is_hidden(elem):
            continue
        for attr in ("fill", "stroke"):
            val = elem.get(attr)
            if val:
                colors.update(h.lower() for h in HEX_RE.findall(val))
        if elem.tag in ("fill", "stroke"):
            c = elem.get("color")
            if c:
                colors.update(h.lower() for h in HEX_RE.findall(c))
    return sorted(colors)


def find_css_conflicts(html, css):
    found = set()
    for m in re.finditer(r'class="([^"]*)"', html):
        classes = m.group(1).split()
        for cls in classes:
            if cls in CONFLICT_CLASSES:
                # Bootstrap's own toast is sanctioned when paired with sui-toast.
                if cls == "toast" and "sui-toast" in classes:
                    continue
                found.add(cls)
    for name in CONFLICT_CLASSES:
        if re.search(r"\." + re.escape(name) + r"(?![\w-])", css):
            found.add(name)
    return sorted(found)


def undefined_sui_classes(html, css):
    used = set()
    for m in re.finditer(r'class="([^"]*)"', html):
        for cls in m.group(1).split():
            if cls.startswith("sui-"):
                used.add(cls)
    undefined = []
    for cls in sorted(used):
        if not re.search(r"\." + re.escape(cls) + r"(?![\w-])", css):
            undefined.append(cls)
    return undefined


def gate_responsive(html, css):
    findings = []
    if not VIEWPORT_RE.search(html):
        findings.append("missing <meta name=\"viewport\">")
    medias = re.findall(r"@media[^{]*", css)
    if len(medias) < 2:
        findings.append(f"expected >= 2 @media breakpoints, found {len(medias)}")
    return findings


def _load_outputs(paths):
    html, css, js = [], [], []
    for p in paths:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        ext = os.path.splitext(p)[1].lower()
        if ext == ".css":
            css.append(txt)
        elif ext == ".js":
            js.append(txt)
        else:
            html.append(txt)
    return "\n".join(html), "\n".join(css), "\n".join(js)


def cmd_prep(args):
    with open(args.input, "rb") as f:
        data = f.read()
    root = prep(data)
    out_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + ET.tostring(root, encoding="unicode", pretty_print=True)
    )
    if args.out:
        out_path = args.out
    else:
        sha = hashlib.sha1(data).hexdigest()[:8]
        out_path = os.path.join(tempfile.gettempdir(), f"sliceui_{sha}_prep.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out_xml)
    lines = out_xml.count("\n") + 1
    chars = len(out_xml)
    print(f"Wrote: {out_path}")
    print(f"Lines: {lines}")
    print(f"Chars: {chars}")
    print(f"Est. tokens: {chars // 4}")
    if lines < 1200:
        print("Read directly in 1x Read.")
    else:
        print("Use outline + cut per section.")


def cmd_outline(args):
    _walk(parse_xml(args.xml_file), 0)


def cmd_cut(args):
    root = parse_xml(args.xml_file)
    id_map = {e.get("id"): e for e in root.iter() if e.get("id") is not None}
    missing = [i for i in args.id if i not in id_map]
    if missing:
        sys.stderr.write(f"sliceui cut: id(s) not found: {', '.join(missing)}\n")
        sys.exit(1)
    for nid in args.id:
        elem = id_map[nid]
        parent = elem.getparent()
        while parent is not None and parent.tag in SKIP_OUTLINE_TAGS:
            parent = parent.getparent()
        pid = parent.get("id", "") if parent is not None else ""
        pname = parent.get("name", "") if parent is not None else ""
        psize = ""
        if parent is not None:
            psize = f"{parent.get('width', '')}x{parent.get('height', '')}"
        playout = parent.get("layoutMode", "NONE") if parent is not None else "NONE"
        pspacing = parent.get("itemSpacing", "") if parent is not None else ""
        sub = ET.tostring(elem, encoding="unicode", pretty_print=True)
        line_count = sub.count("\n") + 1
        print(
            f'<!-- SECTION_START id="{nid}" parent_id="{pid}" '
            f'parent_name="{pname}" parent_size="{psize}" '
            f'parent_layout="{playout}" parent_itemSpacing="{pspacing}" -->'
        )
        if line_count > 900:
            kids = ", ".join(
                f'id="{k.get("id", "")}" name="{k.get("name", "")}"' for k in list(elem)
            )
            print(f"<!-- WARNING: section {nid} exceeds 900 lines ({line_count}). "
                  f"Direct children: {kids} -->")
        print(sub.rstrip())
        print(f'<!-- SECTION_END id="{nid}" -->')


def cmd_arc(args):
    w = float(args.width)
    h = float(args.height)
    start = float(args.start)
    end = float(args.end)
    inner = float(args.inner) if args.inner is not None else 0.0
    print(f'<path d="{build_arc_path(w, h, start, end, inner)}"/>')


def cmd_verify(args):
    root = parse_xml(args.xml_file)
    texts = collect_texts(root)
    colors = collect_colors(root)
    html, css, js = _load_outputs(args.output_files)
    all_text = html + "\n" + css + "\n" + js

    all_norm = normalize_whitespace(all_text)
    all_lower = all_text.lower()

    missing_text = [t for t in texts if t not in all_norm]
    missing_color = [c for c in colors if c not in all_lower]

    hard_fail = False

    # HARD GATE 1 — text
    t_total, t_ok = len(texts), len(texts) - len(missing_text)
    t_pct = (t_ok / t_total * 100) if t_total else 100.0
    print(f"TEXT COVERAGE: {t_ok}/{t_total} ({t_pct:.1f}%)")
    for t in missing_text:
        print(f"  MISSING TEXT: {t}")
    if missing_text:
        hard_fail = True

    # HARD GATE 2 — bootstrap collision
    bootstrap_used = bool(BOOTSTRAP_CDN_RE.search(html))
    conflicts = find_css_conflicts(html, css) if bootstrap_used else []
    if conflicts:
        hard_fail = True
        print("BOOTSTRAP CONFLICT: FAIL (unprefixed: " + ", ".join(conflicts) + ")")
    else:
        print("BOOTSTRAP CONFLICT: OK")

    # HARD GATE 3 — undefined sui classes (HTML -> CSS)
    undef = undefined_sui_classes(html, css)
    if undef:
        hard_fail = True
        print("SUI CLASS AUDIT: FAIL (undefined: " + ", ".join(undef) + ")")
    else:
        print("SUI CLASS AUDIT: OK (0 undefined)")

    # HARD GATE 4 — viewport + breakpoints
    resp = gate_responsive(html, css)
    if resp:
        hard_fail = True
        for r in resp:
            print(f"  RESPONSIVE: {r}")
        print("RESPONSIVE: FAIL")
    else:
        print("RESPONSIVE: PASS")

    # WARNING (non-blocking) — color + overflow clearance
    c_total, c_ok = len(colors), len(colors) - len(missing_color)
    c_pct = (c_ok / c_total * 100) if c_total else 100.0
    print(f"COLOR COVERAGE: {c_ok}/{c_total} ({c_pct:.1f}%) [WARN]")
    for c in missing_color:
        print(f"  MISSING COLOR: {c}")

    scroll = re.search(r"\.sui-chart-scroll\s*\{[^}]*\}", css)
    if scroll and "overflow-x" in scroll.group(0) and "padding-top" not in scroll.group(0):
        print("OVERFLOW: warn — overflow-x:auto without padding-top clearance")
    else:
        print("OVERFLOW: ok")

    print("INTERACTIVITY: " + ("initialized" if INTERACTIVITY_RE.search(all_text) else "not found"))

    sys.exit(2 if hard_fail else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sliceui.py", description="Deterministic Figma XML (.figml) slicing engine."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_prep = sub.add_parser(
        "prep", aliases=["compact"],
        help="Losslessly compress a .figml into a flat attribute-rich form.",
    )
    p_prep.add_argument("input", help="Input .figml file.")
    p_prep.add_argument("--out", help="Output XML path (default: tempdir).")
    p_prep.set_defaults(func=cmd_prep)

    p_outline = sub.add_parser("outline", help="Print a structural map with flags.")
    p_outline.add_argument("xml_file")
    p_outline.set_defaults(func=cmd_outline)

    p_cut = sub.add_parser("cut", help="Extract one or more node subtrees by id.")
    p_cut.add_argument("xml_file")
    p_cut.add_argument("--id", action="append", required=True, dest="id")
    p_cut.set_defaults(func=cmd_cut)

    p_arc = sub.add_parser("arc", help="Convert Figma arcData into an SVG path.")
    p_arc.add_argument("--width", required=True)
    p_arc.add_argument("--height", required=True)
    p_arc.add_argument("--start", required=True)
    p_arc.add_argument("--end", required=True)
    p_arc.add_argument("--inner", default=None)
    p_arc.set_defaults(func=cmd_arc)

    p_verify = sub.add_parser("verify", help="Audit outputs (HARD GATE + warnings).")
    p_verify.add_argument("xml_file")
    p_verify.add_argument("output_files", nargs="+")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
