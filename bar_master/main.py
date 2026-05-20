import arcadia
import json
import math
import time

EXTENSION_ID = "bar-master"

arcadia.register_module(
    name=EXTENSION_ID,
    version="0.5.0",
    description="Who needs a bartender when you own the bar? Bartending is temporary. Mastery is forever. Customize your macOS menu bar without limits.",
    permissions=["overlay.hud", "cursor.global_position", "system.accessibility"],
    platforms=["macos"],
    tags=["stable", "menu-bar", "overlay"],
)

_DEFAULT_GRADIENT = json.dumps([
    {"pos": 0.0, "color": "#1a1a2e"},
    {"pos": 1.0, "color": "#16213e"},
])

def _corner_token(key, label, vis):
    return {"key": key, "label": label, "kind": "int",
            "default": 0, "min": 0, "max": 20, "visible_when": vis}


# Custom-shape per-corner radius sliders. 4 when the bar is one piece; 8 when "Isolated
# Areas" splits it into a left and right section, each independently rounded.
_VIS_CUSTOM_SOLO = {"all": [
    {"token": "style", "ne": "blur"},
    {"token": "shape", "eq": "custom"},
    {"token": "isolated", "ne": "true"},
]}
_VIS_CUSTOM_ISO = {"all": [
    {"token": "style", "ne": "blur"},
    {"token": "shape", "eq": "custom"},
    {"token": "isolated", "eq": "true"},
]}

_CORNER_TOKENS = [
    _corner_token("radius_tl", "Top Left",     _VIS_CUSTOM_SOLO),
    _corner_token("radius_tr", "Top Right",    _VIS_CUSTOM_SOLO),
    _corner_token("radius_br", "Bottom Right", _VIS_CUSTOM_SOLO),
    _corner_token("radius_bl", "Bottom Left",  _VIS_CUSTOM_SOLO),
    _corner_token("radius_l_tl", "Left · Top Left",     _VIS_CUSTOM_ISO),
    _corner_token("radius_l_tr", "Left · Top Right",    _VIS_CUSTOM_ISO),
    _corner_token("radius_l_br", "Left · Bottom Right", _VIS_CUSTOM_ISO),
    _corner_token("radius_l_bl", "Left · Bottom Left",  _VIS_CUSTOM_ISO),
    _corner_token("radius_r_tl", "Right · Top Left",     _VIS_CUSTOM_ISO),
    _corner_token("radius_r_tr", "Right · Top Right",    _VIS_CUSTOM_ISO),
    _corner_token("radius_r_br", "Right · Bottom Right", _VIS_CUSTOM_ISO),
    _corner_token("radius_r_bl", "Right · Bottom Left",  _VIS_CUSTOM_ISO),
]

arcadia.register_tokens(EXTENSION_ID, [
    {
        "key": "enabled",
        "label": "Enabled",
        "kind": "bool",
        "default": True,
    },
    {
        "key": "style",
        "label": "Style",
        "kind": "string",
        "default": "gradient",
        "options": ["gradient", "solid", "blur"],
    },

    # ── Gradient ──────────────────────────────────────────────────────────────
    {
        "key": "gradient",
        "label": "Gradient",
        "kind": "gradient",
        "default": _DEFAULT_GRADIENT,
        "visible_when": {"token": "style", "eq": "gradient"},
    },
    {
        "key": "gradient_dir",
        "label": "Direction",
        "kind": "string",
        "default": "horizontal",
        "options": ["horizontal", "vertical", "diagonal"],
        "visible_when": {"token": "style", "eq": "gradient"},
    },

    # ── Solid colour ──────────────────────────────────────────────────────────
    {
        "key": "color",
        "label": "Color",
        "kind": "color",
        "default": "#1a1a2e",
        "visible_when": {"token": "style", "eq": "solid"},
    },

    # ── Opacity (solid + gradient) ────────────────────────────────────────────
    {
        "key": "opacity",
        "label": "Opacity",
        "kind": "int",
        "default": 90,
        "min": 0,
        "max": 100,
        "visible_when": {"token": "style", "ne": "blur"},
    },

    # ── Blur material ──────────────────────────────────────────────────────────
    {
        "key": "blur_material",
        "label": "Material",
        "kind": "string",
        "default": "sidebar",
        "options": ["sidebar", "menu", "titlebar", "hud", "popover", "fullscreen"],
        "visible_when": {"token": "style", "eq": "blur"},
    },

    # ── Shape ──────────────────────────────────────────────────────────────────
    {
        "key": "shape",
        "label": "Shape",
        "kind": "string",
        "default": "full",
        "options": ["full", "pill", "custom"],
        "visible_when": {"token": "style", "ne": "blur"},
    },
    # ── Corner radius (full mode only) ────────────────────────────────────────
    {
        "key": "corner_radius",
        "label": "Corner Radius",
        "kind": "int",
        "default": 0,
        "min": 0,
        "max": 20,
        "visible_when": {
            "all": [
                {"token": "shape", "eq": "full"},
                {"token": "style", "ne": "blur"},
            ]
        },
    },
    # ── Per-corner radius (custom mode) ───────────────────────────────────────
    *_CORNER_TOKENS,

    # ── Isolated areas ────────────────────────────────────────────────────────
    {
        "key": "isolated",
        "label": "Isolated Areas",
        "kind": "bool",
        "default": False,
    },
    {
        "key": "size_to_contents",
        "label": "Size to Contents",
        "kind": "bool",
        "default": False,
        "visible_when": {"token": "isolated", "eq": "true"},
    },
    {
        "key": "content_padding",
        "label": "Content Padding",
        "kind": "int",
        "default": 10,
        "min": 0,
        "max": 60,
        "visible_when": {
            "all": [
                {"token": "isolated", "eq": "true"},
                {"token": "size_to_contents", "eq": "true"},
            ]
        },
    },
    {
        "key": "left_section_pct",
        "label": "Left Section Width %",
        "kind": "int",
        "default": 40,
        "min": 10,
        "max": 90,
        "visible_when": {
            "all": [
                {"token": "isolated", "eq": "true"},
                {"token": "size_to_contents", "ne": "true"},
            ]
        },
    },
    {
        "key": "right_section_pct",
        "label": "Right Section Width %",
        "kind": "int",
        "default": 30,
        "min": 10,
        "max": 90,
        "visible_when": {
            "all": [
                {"token": "isolated", "eq": "true"},
                {"token": "size_to_contents", "ne": "true"},
            ]
        },
    },

    # ── Border ────────────────────────────────────────────────────────────────
    {
        "key": "border_enabled",
        "label": "Border",
        "kind": "bool",
        "default": False,
        "visible_when": {"token": "style", "ne": "blur"},
    },
    {
        "key": "border_color",
        "label": "Border Color",
        "kind": "color",
        "default": "#ffffff",
        "visible_when": {
            "all": [
                {"token": "border_enabled", "eq": "true"},
                {"token": "style", "ne": "blur"},
            ]
        },
    },
    {
        "key": "border_thickness",
        "label": "Border Thickness",
        "kind": "int",
        "default": 1,
        "min": 1,
        "max": 8,
        "visible_when": {
            "all": [
                {"token": "border_enabled", "eq": "true"},
                {"token": "style", "ne": "blur"},
            ]
        },
    },

    # ── Shadow ────────────────────────────────────────────────────────────────
    {
        "key": "shadow_enabled",
        "label": "Shadow",
        "kind": "bool",
        "default": False,
        "visible_when": {"token": "style", "ne": "blur"},
    },
    {
        "key": "shadow_opacity",
        "label": "Shadow Opacity",
        "kind": "int",
        "default": 60,
        "min": 0,
        "max": 100,
        "visible_when": {
            "all": [
                {"token": "shadow_enabled", "eq": "true"},
                {"token": "style", "ne": "blur"},
            ]
        },
    },
    {
        "key": "shadow_size",
        "label": "Shadow Size",
        "kind": "int",
        "default": 8,
        "min": 2,
        "max": 24,
        "visible_when": {
            "all": [
                {"token": "shadow_enabled", "eq": "true"},
                {"token": "style", "ne": "blur"},
            ]
        },
    },

    # ── Mission Control ───────────────────────────────────────────────────────
    {
        "key": "hide_in_mission_control",
        "label": "Hide in Mission Control",
        "kind": "bool",
        "default": True,
    },

    # ── Animation (gradient only) ─────────────────────────────────────────────
    {
        "key": "animate",
        "label": "Animate",
        "kind": "bool",
        "default": False,
        "visible_when": {"token": "style", "eq": "gradient"},
    },
    {
        "key": "animate_speed",
        "label": "Speed",
        "kind": "string",
        "default": "medium",
        "options": ["slow", "medium", "fast"],
        "visible_when": {
            "all": [
                {"token": "animate", "eq": "true"},
                {"token": "style", "eq": "gradient"},
            ]
        },
    },
])


# ── Token helpers ──────────────────────────────────────────────────────────────

def _b(val, default=False):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes")


def _i(val, default=0):
    try:
        return int(val)
    except Exception:
        return default


# ── Colour helpers ─────────────────────────────────────────────────────────────

def _hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(a, b, t):
    return a + (b - a) * t


def _parse_stops(raw):
    try:
        data = json.loads(raw)
        stops = []
        for item in data:
            pos = max(0.0, min(1.0, float(item["pos"])))
            r, g, b = _hex_to_rgb(item["color"])
            stops.append((pos, r, g, b))
        stops.sort(key=lambda s: s[0])
        if len(stops) >= 2:
            return stops
    except Exception:
        pass
    return [(0.0, 26, 26, 46), (1.0, 22, 33, 62)]


def _sample_gradient(stops, t):
    t = t % 1.0
    if t <= stops[0][0]:
        return stops[0][1], stops[0][2], stops[0][3]
    if t >= stops[-1][0]:
        return stops[-1][1], stops[-1][2], stops[-1][3]
    for i in range(len(stops) - 1):
        pa, ra, ga, ba = stops[i]
        pb, rb, gb, bb = stops[i + 1]
        if pa <= t <= pb:
            span = pb - pa
            f = (t - pa) / span if span > 1e-6 else 0.0
            return int(_lerp(ra, rb, f)), int(_lerp(ga, gb, f)), int(_lerp(ba, bb, f))
    return stops[-1][1], stops[-1][2], stops[-1][3]


# ── Shape helpers ──────────────────────────────────────────────────────────────

def _corner_radius_px(tokens, key, scale):
    """Read a per-corner radius token (logical points) and scale to physical pixels."""
    return max(0, round(min(20, _i(tokens.get(key, 0), 0)) * scale))


def _rounded_rect_sdf_4(fx, fy, x0, y0, w, h, r_tl, r_tr, r_br, r_bl):
    """Signed distance (negative inside, positive outside) from sample point (fx, fy) to a
    rectangle with independent per-corner radii. Sample at pixel centres (x + 0.5)."""
    px = fx - x0 - w * 0.5
    py = fy - y0 - h * 0.5
    if   py < 0.0 and px < 0.0: r = r_tl
    elif py < 0.0:              r = r_tr
    elif px < 0.0:              r = r_bl
    else:                       r = r_br
    r  = max(0.0, min(r, w * 0.5, h * 0.5))
    dx = abs(px) - w * 0.5 + r
    dy = abs(py) - h * 0.5 + r
    return (math.sqrt(max(dx, 0.0) ** 2 + max(dy, 0.0) ** 2)
            + min(max(dx, dy), 0.0) - r)


def _rounded_rect_coverage_4(px, py, x0, y0, w, h, r_tl, r_tr, r_br, r_bl):
    """Fast analytic coverage estimate (single SDF sample at the pixel centre).
    Used to classify pixels; curved edges are refined via `_rr_super`."""
    sdf = _rounded_rect_sdf_4(px + 0.5, py + 0.5, x0, y0, w, h, r_tl, r_tr, r_br, r_bl)
    return max(0.0, min(1.0, 0.5 - sdf))


_CUSTOM_AA = 4  # NxN supersampling for custom-shape curved edges (matches pill path)


def _rr_super(px, py, x0, y0, w, h, r_tl, r_tr, r_br, r_bl, inset=0.0):
    """Supersampled inside-fraction for the per-corner rounded rect. `inset` shifts the
    threshold (sdf < inset) so a grown shape can be sampled for border rings."""
    hits = 0
    step = 1.0 / _CUSTOM_AA
    for sy in range(_CUSTOM_AA):
        fy = py + (sy + 0.5) * step
        for sx in range(_CUSTOM_AA):
            fx = px + (sx + 0.5) * step
            if _rounded_rect_sdf_4(fx, fy, x0, y0, w, h, r_tl, r_tr, r_br, r_bl) < inset:
                hits += 1
    return hits / (_CUSTOM_AA * _CUSTOM_AA)


def _bottom_rounded_coverage(px, py, x0, y0, w, h, r):
    """Anti-aliased coverage for a rect with rounded bottom corners only."""
    if not (x0 <= px < x0 + w and y0 <= py < y0 + h):
        return 0.0
    if r <= 0 or py < y0 + h - r:
        return 1.0
    cx = max(x0 + r, min(px, x0 + w - r))
    sdf = math.sqrt((px - cx) ** 2 + (py - (y0 + h - r)) ** 2) - r
    return max(0.0, min(1.0, 0.5 - sdf))


# ── Sprite builder ─────────────────────────────────────────────────────────────

def _build_sprite(tokens, screen_w, bar_h, phase=0.0, scale=1.0, sections=None):
    """
    Build RGBA sprite bytes for the menu bar.

    `sections` is a list of `(x0_phys, x1_phys)` physical-pixel ranges to render.
    None → single full-width section [(0, screen_w)].
    """
    if sections is None:
        sections = [(0, screen_w)]

    opacity   = max(0, min(100, _i(tokens.get("opacity", 90), 90)))
    alpha     = int(opacity / 100 * 255)
    style     = tokens.get("style", "gradient")
    shape     = tokens.get("shape", "full")
    isolated  = _b(tokens.get("isolated", False))
    direction = tokens.get("gradient_dir", "horizontal")
    radius    = max(0, round(min(20, _i(tokens.get("corner_radius", 0), 0)) * scale))

    shadow_on = _b(tokens.get("shadow_enabled"))
    s_opacity = max(0, min(100, _i(tokens.get("shadow_opacity", 60), 60)))
    s_size    = max(1, round(min(24, _i(tokens.get("shadow_size", 8), 8)) * scale))
    s_alpha   = int(s_opacity / 100 * 255)

    border_on = _b(tokens.get("border_enabled"))
    b_thick   = max(1, round(min(8, _i(tokens.get("border_thickness", 1), 1)) * scale))
    try:
        br, bg_, bb_ = _hex_to_rgb(tokens.get("border_color", "#ffffff"))
    except Exception:
        br, bg_, bb_ = 255, 255, 255

    pill_r = bar_h // 2

    shadow_shift = 0
    total_h = (bar_h
               + (b_thick if border_on else 0)
               + shadow_shift
               + (s_size if shadow_on else 0))
    shadow_y0 = bar_h + (b_thick if border_on else 0) + shadow_shift
    w   = max(1, screen_w)
    rgba = bytearray(w * total_h * 4)

    stops = None
    solid_rgb = None
    if style == "gradient":
        stops = _parse_stops(tokens.get("gradient", _DEFAULT_GRADIENT))
    elif style == "solid":
        try:
            solid_rgb = _hex_to_rgb(tokens.get("color", "#1a1a2e"))
        except Exception:
            solid_rgb = (26, 26, 46)

    dw = max(w - 1, 1)
    dh = max(bar_h - 1, 1)

    def _color(x, y):
        if style == "solid":
            return solid_rgb
        if direction == "vertical":
            t = (y / dh + phase) % 1.0
        elif direction == "diagonal":
            t = ((x / dw + y / dh) / 2.0 + phase) % 1.0
        else:
            t = (x / dw + phase) % 1.0
        return _sample_gradient(stops, t)

    # col_visible tracks which columns have bar content (for full-shape shadow).
    col_visible = bytearray(w)

    for _sect_idx, (sect_x0, sect_x1) in enumerate(sections):
        sect_x0 = max(0, int(sect_x0))
        sect_x1 = min(w, int(sect_x1))
        if sect_x1 <= sect_x0:
            continue
        sect_w = sect_x1 - sect_x0

        if shape == "pill":
            SUPER = 4
            S2    = SUPER * SUPER
            lcx   = sect_x0 + pill_r          # left  circle centre x
            rcx   = sect_x1 - pill_r          # right circle centre x
            ccy   = pill_r                    # both circles share this y centre
            r2    = pill_r * pill_r
            r_out2 = (pill_r + b_thick) ** 2 if border_on else 0

            def _circle_hits(px, py, cx, _r2=r2, _ccy=ccy):
                h = 0
                for sy in range(SUPER):
                    fy = py + (sy + 0.5) / SUPER
                    dy = fy - _ccy; dy2 = dy * dy
                    for sx in range(SUPER):
                        fx = px + (sx + 0.5) / SUPER
                        dx = fx - cx
                        if dx * dx + dy2 <= _r2:
                            h += 1
                return h

            def _ring_hits(px, py, cx, _r2=r2, _r_out2=r_out2, _ccy=ccy):
                h = 0
                for sy in range(SUPER):
                    fy = py + (sy + 0.5) / SUPER
                    dy = fy - _ccy; dy2 = dy * dy
                    for sx in range(SUPER):
                        fx = px + (sx + 0.5) / SUPER
                        dx = fx - cx
                        d2 = dx * dx + dy2
                        if _r2 < d2 <= _r_out2:
                            h += 1
                return h

            # Left circle end
            for y in range(bar_h):
                row_off = y * w * 4
                for x in range(max(0, sect_x0), min(w, lcx + 1)):
                    h = _circle_hits(x, y, lcx)
                    if h == 0:
                        continue
                    r_, g_, b_ = _color(x, y)
                    rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                        bytes([r_, g_, b_, int(h / S2 * alpha)]))
                    if h > S2 // 2:
                        col_visible[x] = 1

            # Right circle end
            for y in range(bar_h):
                row_off = y * w * 4
                for x in range(max(0, rcx), min(w, sect_x1 + 1)):
                    h = _circle_hits(x, y, rcx)
                    if h == 0:
                        continue
                    r_, g_, b_ = _color(x, y)
                    rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                        bytes([r_, g_, b_, int(h / S2 * alpha)]))
                    if h > S2 // 2:
                        col_visible[x] = 1

            # Interior rectangle — runs after circles so full alpha overwrites boundary pixels.
            ix0 = max(0, lcx)
            ix1 = min(w, rcx + 1)
            if ix0 < ix1:
                for y in range(bar_h):
                    row_off = y * w * 4
                    if style == "solid" or direction == "vertical":
                        r_, g_, b_ = _color(ix0, y)
                        chunk = bytes([r_, g_, b_, alpha]) * (ix1 - ix0)
                        rgba[row_off + ix0 * 4:row_off + ix1 * 4] = chunk
                    else:
                        for x in range(ix0, ix1):
                            r_, g_, b_ = _color(x, y)
                            rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                                bytes([r_, g_, b_, alpha]))
                col_visible[ix0:ix1] = b'\x01' * (ix1 - ix0)

            # Pill border: circle rings + bottom strip
            if border_on:
                for y in range(min(total_h, bar_h + b_thick)):
                    row_off = y * w * 4
                    for x in range(max(0, sect_x0 - b_thick - 1), min(w, lcx + 2)):
                        h = _ring_hits(x, y, lcx)
                        if h == 0:
                            continue
                        rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                            bytes([br, bg_, bb_, int(h / S2 * 255)]))
                    for x in range(max(0, rcx - 1), min(w, sect_x1 + b_thick + 2)):
                        h = _ring_hits(x, y, rcx)
                        if h == 0:
                            continue
                        rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                            bytes([br, bg_, bb_, int(h / S2 * 255)]))
                bx0 = max(0, lcx + 1)
                bx1 = min(w, rcx)
                if bx0 < bx1:
                    bchunk = bytes([br, bg_, bb_, 255]) * (bx1 - bx0)
                    for y in range(bar_h, min(total_h, bar_h + b_thick)):
                        row_off = y * w * 4
                        rgba[row_off + bx0 * 4:row_off + bx1 * 4] = bchunk

            # Shadow / outer glow per section (pill)
            if shadow_on and s_size > 0:
                glow_min = float(b_thick) + 1.0 if border_on else 0.0

                for y in range(pill_r, total_h):
                    row_off = y * w * 4
                    qy = float(abs(y - pill_r))
                    max_qx2 = (s_size + pill_r) ** 2 - qy * qy
                    if max_qx2 <= 0:
                        continue
                    max_qx = math.sqrt(max_qx2)

                    # Left end zone
                    for x in range(max(0, int(math.ceil(lcx - max_qx))), lcx):
                        qx   = float(lcx - x)
                        dist = math.sqrt(qx * qx + qy * qy) - pill_r
                        if dist <= glow_min or dist > s_size:
                            continue
                        s_a = int(s_alpha * math.exp(-dist * 4.0 / s_size))
                        if s_a > 0:
                            rgba[row_off + x * 4:row_off + x * 4 + 4] = bytes([0, 0, 0, s_a])

                    # Center strip (below pill only)
                    if y >= bar_h:
                        dy = float(y - bar_h)
                        if glow_min < dy <= s_size:
                            s_a_c = int(s_alpha * math.exp(-dy * 4.0 / s_size))
                            if s_a_c > 0:
                                cx0 = max(0, lcx)
                                cx1 = min(w, rcx + 1)
                                if cx0 < cx1:
                                    rgba[row_off + cx0 * 4:row_off + cx1 * 4] = (
                                        bytes([0, 0, 0, s_a_c]) * (cx1 - cx0))

                    # Right end zone
                    for x in range(rcx + 1, min(w, int(rcx + max_qx) + 2)):
                        qx   = float(x - rcx)
                        dist = math.sqrt(qx * qx + qy * qy) - pill_r
                        if dist <= glow_min or dist > s_size:
                            continue
                        s_a = int(s_alpha * math.exp(-dist * 4.0 / s_size))
                        if s_a > 0:
                            rgba[row_off + x * 4:row_off + x * 4 + 4] = bytes([0, 0, 0, s_a])

        else:
            # Full / custom shape — render within [sect_x0, sect_x1].
            # "custom" → per-corner radii; isolated splits into left/right token sets.
            if shape == "custom":
                if isolated:
                    pfx = "radius_l_" if _sect_idx == 0 else "radius_r_"
                else:
                    pfx = "radius_"
                r_tl = _corner_radius_px(tokens, pfx + "tl", scale)
                r_tr = _corner_radius_px(tokens, pfx + "tr", scale)
                r_br = _corner_radius_px(tokens, pfx + "br", scale)
                r_bl = _corner_radius_px(tokens, pfx + "bl", scale)
            else:
                r_tl = r_tr = r_br = r_bl = radius
            custom_aa = shape == "custom" and (r_tl or r_tr or r_br or r_bl)
            for y in range(bar_h):
                row_off = y * w * 4
                for x in range(sect_x0, sect_x1):
                    cov = _rounded_rect_coverage_4(
                        x, y, sect_x0, 0, sect_w, bar_h, r_tl, r_tr, r_br, r_bl)
                    if cov <= 0.0:
                        continue
                    # Supersample only partial-coverage (curved-edge) pixels.
                    if custom_aa and cov < 1.0:
                        cov = _rr_super(
                            x, y, sect_x0, 0, sect_w, bar_h, r_tl, r_tr, r_br, r_bl)
                        if cov <= 0.0:
                            continue
                    r_, g_, b_ = _color(x, y)
                    rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                        bytes([r_, g_, b_, int(cov * alpha)]))
                    if cov > 0.5:
                        col_visible[x] = 1

            if shape == "custom":
                # Border ring tracing the per-corner radii: coverage of the shape grown
                # by b_thick, minus the fill coverage → an anti-aliased outline.
                if border_on:
                    for y in range(min(total_h, bar_h + b_thick)):
                        row_off = y * w * 4
                        for x in range(max(0, sect_x0 - b_thick),
                                        min(w, sect_x1 + b_thick)):
                            outer = _rr_super(
                                x, y, sect_x0, 0, sect_w, bar_h,
                                r_tl, r_tr, r_br, r_bl, b_thick)
                            if outer <= 0.0:
                                continue
                            fill = _rr_super(
                                x, y, sect_x0, 0, sect_w, bar_h,
                                r_tl, r_tr, r_br, r_bl, 0.0)
                            ring = outer - fill
                            if ring <= 0.0:
                                continue
                            rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                                bytes([br, bg_, bb_, int(ring * 255)]))

                # Drop-shadow glow: exponential falloff by distance outside the outer
                # (border) edge. Only paints empty pixels, so it never covers the bar.
                if shadow_on and s_size > 0:
                    edge = float(b_thick) if border_on else 0.0
                    for y in range(min(total_h, bar_h + b_thick + s_size)):
                        row_off = y * w * 4
                        for x in range(max(0, sect_x0 - b_thick - s_size),
                                        min(w, sect_x1 + b_thick + s_size)):
                            if rgba[row_off + x * 4 + 3] != 0:
                                continue
                            sdf = _rounded_rect_sdf_4(
                                x + 0.5, y + 0.5, sect_x0, 0, sect_w, bar_h,
                                r_tl, r_tr, r_br, r_bl)
                            dist = sdf - edge
                            if dist <= 0.0 or dist > s_size:
                                continue
                            s_a = int(s_alpha * math.exp(-dist * 4.0 / s_size))
                            if s_a > 0:
                                rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                                    bytes([0, 0, 0, s_a]))
            else:
                if border_on:
                    for y in range(bar_h, min(total_h, bar_h + b_thick)):
                        row_off = y * w * 4
                        for x in range(sect_x0, sect_x1):
                            if not col_visible[x]:
                                continue
                            rgba[row_off + x * 4:row_off + x * 4 + 4] = (
                                bytes([br, bg_, bb_, 255]))

                # Shadow for full shape
                if shadow_on and s_size > 0:
                    for i in range(s_size):
                        s_a = int(s_alpha * math.exp(-i * 4.0 / s_size))
                        if s_a <= 0:
                            break
                        y = shadow_y0 + i
                        if y >= total_h:
                            break
                        row_off = y * w * 4
                        for x in range(sect_x0, sect_x1):
                            if not col_visible[x]:
                                continue
                            rgba[row_off + x * 4:row_off + x * 4 + 4] = bytes([0, 0, 0, s_a])

    return bytes(rgba), w, total_h


# ── Extension state ────────────────────────────────────────────────────────────

_cached_screen_width = 1280
_anim_phase = 0.0
_anim_timer_id = None
_current_tokens = {}
_space_handler_registered = False

# Content-width cache: (left_frac, right_frac) or None.
# Re-queried at most every 2 s — AX result changes when focused app changes.
_content_widths_cache = None
_content_widths_ts = 0.0

# Timer that re-pushes the sprite every 2.1 s when size_to_contents is active but
# the animation timer is not running (animation already calls _push_sprite frequently).
_content_refresh_timer_id = None


def _get_content_widths():
    global _content_widths_cache, _content_widths_ts
    now = time.time()
    if now - _content_widths_ts > 2.0:
        try:
            _content_widths_cache = arcadia.menu_bar_content_widths(EXTENSION_ID)
        except Exception:
            _content_widths_cache = None
        _content_widths_ts = now
    return _content_widths_cache


def _pad_sections(tokens, left_end, right_start, logical_w):
    """Expand size-to-contents sections by `content_padding` logical points so the pills
    have breathing room around the menu text / status items. Keeps a 1pt gap minimum."""
    pad = max(0, _i(tokens.get("content_padding", 10), 10))
    left_end    = min(left_end + pad, logical_w)
    right_start = max(right_start - pad, left_end + 1)
    return [(0, left_end), (right_start, logical_w)]


def _section_bounds_logical(tokens, logical_w):
    """Return list of (x0_logical, x1_logical) sections. Always 2 entries in isolated mode."""
    if not _b(tokens.get("isolated", False)):
        return [(0, logical_w)]

    if _b(tokens.get("size_to_contents", False)):
        fracs = _get_content_widths()
        if fracs is not None:
            left_frac, right_frac = fracs
            left_end    = round(left_frac * logical_w)
            right_start = round(right_frac * logical_w)
            # right_start is always valid (ControlCenter always has items).
            # left_end may be 0 when the focused app has no menu items (e.g. Arcadia itself);
            # in that case fall back to the pct slider for the left section width.
            if right_start < logical_w:
                if left_end <= 0:
                    left_pct = max(10, min(90, _i(tokens.get("left_section_pct", 40), 40)))
                    left_end = round(logical_w * left_pct / 100)
                if 0 < left_end < right_start:
                    return _pad_sections(tokens, left_end, right_start, logical_w)
        # Notch fallback: on notch Macs without AX permission, notch geometry
        # gives a reasonable approximation of the left/right section boundaries.
        # Values are in NSScreen logical points (same space as logical_w on standard setups).
        try:
            notch = arcadia.menu_bar_notch_widths(EXTENSION_ID)
            if notch is not None:
                left_end    = round(float(notch[0]))
                right_start = round(float(notch[1]))
                if 0 < left_end < right_start < logical_w:
                    return _pad_sections(tokens, left_end, right_start, logical_w)
        except Exception:
            pass
    left_pct    = max(10, min(90, _i(tokens.get("left_section_pct",  40), 40)))
    right_pct   = max(10, min(90, _i(tokens.get("right_section_pct", 30), 30)))
    left_end    = round(logical_w * left_pct  / 100)
    right_start = logical_w - round(logical_w * right_pct / 100)
    return [(0, left_end), (right_start, logical_w)]


def _push_sprite(tokens, phase=0.0):
    global _cached_screen_width
    size = arcadia.screen_size(EXTENSION_ID)
    scale    = 1.0
    logical_w = _cached_screen_width
    if size:
        physical_w, _ph, scale = size
        logical_w = max(1, int(physical_w / scale))
        _cached_screen_width = logical_w
    os_h       = arcadia.menu_bar_height(EXTENSION_ID) or 0.0
    logical_bh = max(1, int(os_h) - 4)
    phys_w     = max(1, round(logical_w * scale))
    phys_bh    = max(1, round(logical_bh * scale))

    # Compute per-section bounds in physical pixels.
    logical_sections = _section_bounds_logical(tokens, logical_w)
    phys_sections = [(round(x0 * scale), round(x1 * scale)) for (x0, x1) in logical_sections]

    rgba, w, h = _build_sprite(tokens, phys_w, phys_bh, phase, scale=scale, sections=phys_sections)
    arcadia.overlay_hud_set_sprite(
        EXTENSION_ID, rgba, w, h,
        anchor="top-full",
        stacking="below_menu_bar",
        pad_right=0.0,
        pad_bottom=0.0,
        display_width=float(logical_w),
        display_height=float(h / scale),
    )


def _content_refresh_tick():
    global _content_widths_ts
    tokens = _current_tokens
    if not tokens:
        return
    _content_widths_ts = 0.0  # force re-query on next _get_content_widths call
    _push_sprite(tokens)


def _anim_tick():
    global _anim_phase, _current_tokens
    tokens = _current_tokens
    if not tokens:
        return
    if tokens.get("style", "gradient") != "gradient" or not _b(tokens.get("animate")):
        return
    speed   = tokens.get("animate_speed", "medium")
    delta   = {"slow": 0.002, "fast": 0.012}.get(speed, 0.005)
    _anim_phase = (_anim_phase + delta) % 1.0
    _push_sprite(tokens, _anim_phase)


def _clear_all_vibrancy():
    arcadia.overlay_hud_clear_vibrancy(EXTENSION_ID)


def _on_space_change():
    """Fired by the Rust space observer on every active-space transition (no polling)."""
    tokens = _current_tokens
    if not tokens or not _b(tokens.get("enabled"), default=True):
        return
    if not _b(tokens.get("hide_in_mission_control", True)):
        return
    if arcadia.is_mission_control_active(EXTENSION_ID):
        arcadia.overlay_hud_clear_sprite(EXTENSION_ID)
        _clear_all_vibrancy()
    else:
        _refresh(tokens)


def _refresh(tokens):
    global _anim_timer_id, _anim_phase, _current_tokens, _space_handler_registered
    global _content_refresh_timer_id
    _current_tokens = dict(tokens)

    if not _b(tokens.get("enabled"), default=True):
        arcadia.overlay_hud_clear_sprite(EXTENSION_ID)
        _clear_all_vibrancy()
        if _anim_timer_id is not None:
            arcadia.cancel_timer(_anim_timer_id)
            _anim_timer_id = None
        if _content_refresh_timer_id is not None:
            arcadia.cancel_timer(_content_refresh_timer_id)
            _content_refresh_timer_id = None
        if _space_handler_registered:
            arcadia.unregister_space_change_handler(EXTENSION_ID)
            _space_handler_registered = False
        return

    # Register / unregister the event-based space-change handler.
    hide_mc = _b(tokens.get("hide_in_mission_control", True))
    if hide_mc and not _space_handler_registered:
        arcadia.register_space_change_handler(EXTENSION_ID, _on_space_change)
        _space_handler_registered = True
    elif not hide_mc and _space_handler_registered:
        arcadia.unregister_space_change_handler(EXTENSION_ID)
        _space_handler_registered = False

    # Don't render while Mission Control is active.
    if hide_mc and arcadia.is_mission_control_active(EXTENSION_ID):
        arcadia.overlay_hud_clear_sprite(EXTENSION_ID)
        _clear_all_vibrancy()
        if _anim_timer_id is not None:
            arcadia.cancel_timer(_anim_timer_id)
            _anim_timer_id = None
        return

    style    = tokens.get("style", "gradient")
    isolated = _b(tokens.get("isolated", False))

    # Stop animation timer if no longer applicable
    animating = style == "gradient" and _b(tokens.get("animate"))
    if not animating and _anim_timer_id is not None:
        arcadia.cancel_timer(_anim_timer_id)
        _anim_timer_id = None
        _anim_phase    = 0.0

    # Content-widths polling timer: re-push every 2.1 s so sections track the
    # focused app's menu bar width. Not needed when animating (anim tick already
    # calls _push_sprite) or when size_to_contents is off.
    need_content_poll = isolated and _b(tokens.get("size_to_contents", False)) and not animating
    if need_content_poll and _content_refresh_timer_id is None:
        _content_refresh_timer_id = arcadia.set_timer(EXTENSION_ID, 2100, _content_refresh_tick)
    elif not need_content_poll and _content_refresh_timer_id is not None:
        arcadia.cancel_timer(_content_refresh_timer_id)
        _content_refresh_timer_id = None

    if style == "blur":
        arcadia.overlay_hud_clear_sprite(EXTENSION_ID)
        size = arcadia.screen_size(EXTENSION_ID)
        scale = 1.0
        logical_w = _cached_screen_width
        if size:
            physical_w, _ph, scale = size
            logical_w = max(1, int(physical_w / scale))
        os_h     = arcadia.menu_bar_height(EXTENSION_ID) or 0.0
        height   = max(1.0, float(os_h) * scale - 7.0)
        material = tokens.get("blur_material", "sidebar")

        if isolated:
            logical_sections = _section_bounds_logical(tokens, logical_w)
            x_ranges = [(float(s[0]), float(s[1])) for s in logical_sections]
            arcadia.overlay_hud_set_vibrancy(
                EXTENSION_ID, height,
                stacking="below_menu_bar", material=material,
                x_ranges=x_ranges,
            )
        else:
            arcadia.overlay_hud_set_vibrancy(
                EXTENSION_ID, height,
                stacking="below_menu_bar",
                material=material,
            )
        return

    _clear_all_vibrancy()

    if animating:
        _push_sprite(tokens, _anim_phase)
        if _anim_timer_id is None:
            speed         = tokens.get("animate_speed", "medium")
            interval      = {"slow": 150, "fast": 50}.get(speed, 80)
            _anim_timer_id = arcadia.set_timer(EXTENSION_ID, interval, _anim_tick)
    else:
        _push_sprite(tokens, 0.0)


arcadia.register_token_change_handler(EXTENSION_ID, _refresh)
_refresh(arcadia.read_tokens(EXTENSION_ID))
