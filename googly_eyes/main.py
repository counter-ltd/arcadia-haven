"""Googly Eyes — Arcadia tray/menu-bar extension.

Each pupil aims at the OS-global mouse cursor hot spot when `cursor.global_position`
is allowed and `arcadia.cursor_position` returns data. If cursor is unavailable,
pupils fall back toward the primary display center using a per-eye proxy position
(not one shared offset for all eyes).

Tray bounds from `arcadia.tray_icon_screen_bounds` are physical pixels; cursor
readings are mapped into that space using the tuple's `pixels_per_point` per
`TrayBackend::icon_screen_bounds` docs in arcadia-core.

Optional token `separate_eyes`: one menubar/tray icon per eye so icons can be
dragged apart (platform-dependent).

Tokens `blink_on_click` / `relative_blink_on_click`: primary mouse buttons (global, OS-wide when
`cursor.global_mouse_buttons` is granted) draw pupils as short horizontal lines for a moment. With separate
icons, `relative_blink_on_click` uses each icon's on-screen X center so left click winks the
geometrically leftmost eye and right click the rightmost (after the user drags icons apart).

Pupil movement is smoothed via exponential decay (frame-rate-compensated lerp).
Blink open/close is animated using `arcadia.animate()` — a smooth squish from round
pupil to horizontal ellipse and back, rather than an instant toggle.
"""

import math
import random
import time

import arcadia

EXT = "googly-eyes"
MODULE_LABEL = "Googly Eyes"

arcadia.register_module(
    name=EXT,
    version="0.1.0",
    description="Googly eyes in your menu bar / system tray that follow the mouse cursor.",
    permissions=[
        "tray.create",
        "cursor.global_position",
        "cursor.global_mouse_buttons",
    ],
    tags=["stable", "tray", "cursor"],
)

arcadia.register_tokens(
    EXT,
    [
        {
            "key": "emotion",
            "label": "Eye emotion",
            "kind": "string",
            "default": "neutral",
            "options": ["neutral", "sad", "angry"],
        },
        {
            "key": "eye_count",
            "label": "Number of eyes (1-4)",
            "kind": "int",
            "default": 2,
            "min": 1,
            "max": 4,
            "granularity": "whole",
            "visible_when": {"token": "emotion", "eq": "neutral"},
        },
        {"key": "refresh_ms", "label": "Refresh interval (ms)", "kind": "int", "default": 33},
        {"key": "eye_radius_px", "label": "Eye radius (px)", "kind": "int", "default": 10, "min": 2, "max": 20},
        {"key": "pupil_radius_px", "label": "Pupil radius (px)", "kind": "int", "default": 4, "min": 1, "max": 12},
        {
            "key": "eye_spacing_px",
            "label": "Spacing between eyes (px)",
            "kind": "int",
            "default": 2,
            "visible_when": {
                "all": [
                    {"token": "eye_count", "gte": 2},
                    {"token": "separate_eyes", "eq": False},
                ]
            },
        },
        {"key": "outline_width_px", "label": "Outline width (px)", "kind": "int", "default": 1},
        {
            "key": "separate_eyes",
            "label": "Separate eyes (one tray icon per eye — drag apart in menu bar)",
            "kind": "bool",
            "default": False,
        },
        {"key": "sclera_color", "label": "Sclera (white-of-eye) color", "kind": "color", "default": "#ffffff"},
        {"key": "pupil_color", "label": "Pupil color", "kind": "color", "default": "#111111"},
        {"key": "outline_color", "label": "Outline color", "kind": "color", "default": "#111111"},
        {
            "key": "blink_on_click",
            "label": "Blink on click anywhere (pupils become short horizontal lines)",
            "kind": "bool",
            "default": False,
        },
        {
            "key": "relative_blink_on_click",
            "label": "Relative blink: left click → left eye, right click → right eye (≥2 eyes; uses screen position when separate)",
            "kind": "bool",
            "default": False,
            "visible_when": {"token": "eye_count", "gte": 2},
        },
    ],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_hex_color(hex_str, fallback=(255, 255, 255, 255)):
    s = (hex_str or "").lstrip("#")
    if len(s) < 6:
        return fallback
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16) if len(s) >= 8 else 255
        return (r, g, b, a)
    except ValueError:
        return fallback


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _lerp_f(a, b, t):
    return a + (b - a) * t


def _bool_token(tokens, key, default=False):
    v = tokens.get(key)
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "on"):
        return True
    if s in ("0", "false", "no", "off", ""):
        return False
    return default


def _load_config():
    tokens = arcadia.read_tokens(EXT) or {}

    def _i(key, default, lo=None, hi=None):
        try:
            v = int(tokens.get(key, default))
        except (TypeError, ValueError):
            v = default
        if lo is not None and hi is not None:
            v = _clamp(v, lo, hi)
        return v

    raw_emotion = str(tokens.get("emotion", "neutral")).strip().lower()
    emotion = raw_emotion if raw_emotion in ("neutral", "sad", "angry") else "neutral"
    eye_count = _i("eye_count", 2, 1, 4)
    if emotion in ("sad", "angry"):
        eye_count = 2

    return {
        "emotion": emotion,
        "eye_count": eye_count,
        "refresh_ms": _i("refresh_ms", 33, 8, 1000),
        "eye_r": _i("eye_radius_px", 10, 2, 20),
        "pupil_r": _i("pupil_radius_px", 4, 1, 12),
        "spacing": _i("eye_spacing_px", 2, 0, 64),
        "outline": _i("outline_width_px", 1, 0, 8),
        "separate_eyes": _bool_token(tokens, "separate_eyes", False),
        "sclera": _parse_hex_color(tokens.get("sclera_color"), (255, 255, 255, 255)),
        "pupil": _parse_hex_color(tokens.get("pupil_color"), (17, 17, 17, 255)),
        "outline_color": _parse_hex_color(tokens.get("outline_color"), (17, 17, 17, 255)),
        "blink_on_click": _bool_token(tokens, "blink_on_click", False),
        "relative_blink_on_click": _bool_token(tokens, "relative_blink_on_click", False),
    }


def _pupil_target_offsets(cfg, width, height, eye_centers, geom, cursor_pt, screen_wh):
    """Compute raw target (px_off, py_off) per eye toward cursor. Raster Y-down."""
    eye_r = cfg["eye_r"]
    pupil_r = cfg["pupil_r"]
    outline = cfg["outline"]
    max_offset = max(0, eye_r - pupil_r - outline)

    if geom and max_offset > 0 and cursor_pt and width > 0 and height > 0:
        g = tuple(geom)
        if len(g) >= 5:
            tx, ty, tw, th, ppp = g[0], g[1], g[2], g[3], g[4]
        else:
            tx, ty, tw, th = g[0], g[1], g[2], g[3]
            ppp = 1.0
        ppp = float(ppp) if ppp else 1.0
        cxp = float(cursor_pt[0]) * ppp
        cyp = float(cursor_pt[1]) * ppp
        s = min(tw / float(width), th / float(height))
        ox = tx + max(0.0, (tw - width * s) * 0.5)
        oy = ty + max(0.0, (th - height * s) * 0.5)
        out = []
        for ex, ey in eye_centers:
            gx = ox + ex * s
            gy = oy + ey * s
            vx, vy = cxp - gx, cyp - gy
            mag = math.hypot(vx, vy)
            if mag > 1e-9:
                vx /= mag
                vy /= mag
            else:
                vx, vy = 0.0, 0.0
            out.append((vx * max_offset, vy * max_offset))
        return out

    screen_w, screen_h = (screen_wh[0], screen_wh[1]) if screen_wh else (1920, 1080)
    sw = max(1.0, float(screen_w))
    sh = max(1.0, float(screen_h))
    band_y = min(48.0, sh * 0.06)
    if cursor_pt:
        cx, cy = float(cursor_pt[0]), float(cursor_pt[1])
    else:
        cx, cy = sw * 0.5, sh * 0.5

    out = []
    for ex, ey in eye_centers:
        gx = (ex + 0.5) / float(width) * sw
        gy = (ey + 0.5) / float(height) * band_y
        vx, vy = cx - gx, cy - gy
        mag = math.hypot(vx, vy)
        if mag > 1e-9:
            vx /= mag
            vy /= mag
        else:
            vx, vy = 0.0, 0.0
        out.append((vx * max_offset, vy * max_offset))
    return out


def _eye_geometry(cfg, count):
    """Shared layout: eye centers in icon pixel space, width, height."""
    eye_r = cfg["eye_r"]
    pupil_r = cfg["pupil_r"]
    spacing = cfg["spacing"]
    outline = cfg["outline"]
    eye_diameter = (eye_r + outline) * 2
    width = eye_diameter * count + spacing * max(0, count - 1)
    height = eye_diameter
    eye_centers = []
    for i in range(count):
        ex = (eye_r + outline) + i * (eye_diameter + spacing)
        ey = eye_r + outline
        eye_centers.append((ex, ey))
    return eye_r, pupil_r, spacing, outline, eye_diameter, width, height, eye_centers


def _angled_clip_y(eye_r, inner_high, x, ex, ey):
    """Return the Y threshold for the diagonal top-lid clip.

    Pixels with (y + 0.5) < clip_y are outside the eye shape.
    inner_high=True  → inner corner high, outer corner low  (sad)
    inner_high=False → outer corner high, inner corner low  (angry)

    Clip line: inner side at ey - 0.8*eye_r, outer side at ey - 0.2*eye_r.
    For left eye inner=right; for right eye inner=left — caller inverts as needed.
    """
    if inner_high:
        return ey - eye_r * 0.5 + 0.3 * (ex - x)
    else:
        return ey - eye_r * 0.5 + 0.3 * (x - ex)


def _build_base_frame(cfg, eye_centers, width, height, eye_roles=None):
    """Build static background: outline ring + sclera fill, no pupils. Called once per config change."""
    eye_r = cfg["eye_r"]
    outline = cfg["outline"]
    sclera = cfg["sclera"]
    outline_col = cfg["outline_color"]
    eye_r_sq = eye_r ** 2
    eye_r_outer_sq = (eye_r + outline) ** 2
    emotion = cfg.get("emotion", "neutral")
    do_clip = emotion in ("sad", "angry")
    flip_clip = emotion == "angry"
    pixels = bytearray(width * height * 4)
    for y in range(height):
        for x in range(width):
            for i, (ex, ey) in enumerate(eye_centers):
                dx = x + 0.5 - ex
                dy = y + 0.5 - ey
                d_sq = dx * dx + dy * dy
                if d_sq <= eye_r_outer_sq:
                    if do_clip and eye_roles is not None and i < len(eye_roles):
                        inner_high = (not eye_roles[i]) if flip_clip else eye_roles[i]
                        clip_y = _angled_clip_y(eye_r, inner_high, x + 0.5, ex, ey)
                        if y + 0.5 < clip_y:
                            break
                    col = sclera if d_sq <= eye_r_sq else outline_col
                    idx = (y * width + x) * 4
                    pixels[idx] = col[0]
                    pixels[idx + 1] = col[1]
                    pixels[idx + 2] = col[2]
                    pixels[idx + 3] = col[3]
                    break
    return pixels


def _render_rgba(cfg, smooth_offsets, blink_amounts, tray_id, eye_centers, width, height, eye_roles=None):
    """Render frame: copy cached base then paint only pupil pixels in bounding box."""
    eye_r = cfg["eye_r"]
    pupil_r = cfg["pupil_r"]
    outline = cfg["outline"]
    pupil_col = cfg["pupil"]
    emotion = cfg.get("emotion", "neutral")
    do_clip = emotion in ("sad", "angry")
    flip_clip = emotion == "angry"

    # Build cache key for static background — only depends on geometry, colors, and emotion.
    base_key = (
        eye_r, cfg["outline"], cfg["sclera"], cfg["outline_color"],
        width, height, tuple(eye_centers),
        cfg.get("emotion", "neutral"), tuple(eye_roles) if eye_roles else (),
    )
    base = _state.get("_base_cache_val") if _state.get("_base_cache_key") == base_key else None
    if base is None:
        base = _build_base_frame(cfg, eye_centers, width, height, eye_roles)
        _state["_base_cache_key"] = base_key
        _state["_base_cache_val"] = base

    pixels = bytearray(base)  # shallow copy of static layer

    eye_r_sq = eye_r ** 2
    line_half_w = min((eye_r - outline) * 0.6, max(pupil_r * 1.1, 2.0))
    line_half_h = max(0.5, min(1.6, pupil_r * 0.42))
    pr_sq = pupil_r ** 2
    pr, pg, pb, pa = pupil_col

    for i, (ex, ey) in enumerate(eye_centers):
        ox, oy = smooth_offsets[i] if i < len(smooth_offsets) else (0.0, 0.0)
        spin_t = _state["spin_phases"].get((tray_id, i))
        if spin_t is not None:
            s_angle, s_rot, s_max = _state["spin_params"].get((tray_id, i), (0.0, float(_SPIN_ROTATIONS), 0.0))
            angle = spin_t * 2 * math.pi * s_rot + s_angle
            ox = s_max * math.cos(angle)
            oy = s_max * math.sin(angle)
        pcx = ex + ox
        pcy = ey + oy
        blink_amt = blink_amounts.get((tray_id, i), 0.0)

        is_left_eye = (eye_roles[i] if (do_clip and eye_roles and i < len(eye_roles)) else None)

        if blink_amt > 0.001:
            eff_rx = _lerp_f(pupil_r, line_half_w, blink_amt)
            eff_ry = _lerp_f(pupil_r, line_half_h, blink_amt)
            if eff_rx <= 0 or eff_ry <= 0:
                continue
            x0 = max(0, int(pcx - eff_rx) - 1)
            x1 = min(width, int(pcx + eff_rx) + 2)
            y0 = max(0, int(pcy - eff_ry) - 1)
            y1 = min(height, int(pcy + eff_ry) + 2)
            irx2 = 1.0 / (eff_rx * eff_rx)
            iry2 = 1.0 / (eff_ry * eff_ry)
            for py in range(y0, y1):
                for px in range(x0, x1):
                    pdx = px + 0.5 - pcx
                    pdy = py + 0.5 - pcy
                    if pdx * pdx * irx2 + pdy * pdy * iry2 <= 1.0:
                        dx = px + 0.5 - ex
                        dy = py + 0.5 - ey
                        if dx * dx + dy * dy <= eye_r_sq:
                            if is_left_eye is not None:
                                inner_high = (not is_left_eye) if flip_clip else is_left_eye
                                if py + 0.5 < _angled_clip_y(eye_r, inner_high, px + 0.5, ex, ey):
                                    continue
                            idx = (py * width + px) * 4
                            pixels[idx] = pr
                            pixels[idx + 1] = pg
                            pixels[idx + 2] = pb
                            pixels[idx + 3] = pa
        else:
            x0 = max(0, int(pcx - pupil_r) - 1)
            x1 = min(width, int(pcx + pupil_r) + 2)
            y0 = max(0, int(pcy - pupil_r) - 1)
            y1 = min(height, int(pcy + pupil_r) + 2)
            for py in range(y0, y1):
                for px in range(x0, x1):
                    pdx = px + 0.5 - pcx
                    pdy = py + 0.5 - pcy
                    if pdx * pdx + pdy * pdy <= pr_sq:
                        dx = px + 0.5 - ex
                        dy = py + 0.5 - ey
                        if dx * dx + dy * dy <= eye_r_sq:
                            if is_left_eye is not None:
                                inner_high = (not is_left_eye) if flip_clip else is_left_eye
                                if py + 0.5 < _angled_clip_y(eye_r, inner_high, px + 0.5, ex, ey):
                                    continue
                            idx = (py * width + px) * 4
                            pixels[idx] = pr
                            pixels[idx + 1] = pg
                            pixels[idx + 2] = pb
                            pixels[idx + 3] = pa

    return bytes(pixels), width, height


# ─── State ────────────────────────────────────────────────────────────────────

_state = {
    "tray_ids": [],
    "tray_layout_key": None,
    "timer_id": None,
    # Smooth pupil offsets: {(tray_id, eye_idx): (ox, oy)}
    "eye_offsets": {},
    # Animated blink amounts: {(tray_id, eye_idx): float 0.0-1.0}
    "blink_amounts": {},
    # Active blink tween ids: {(tray_id, eye_idx): tween_id}
    "blink_tween_ids": {},
    "mouse_left_prev": False,
    "mouse_right_prev": False,
    "held_wink_keys": set(),
    # Last-rendered state per tray_id for skip-if-unchanged optimisation.
    "last_rendered": {},  # tid -> (smooth_offsets_list, blink_snapshot_dict)
    # Cached FFI results that change infrequently.
    "cached_cfg": None,
    "cached_cfg_at": 0.0,
    "cached_screen": None,
    "cached_screen_at": 0.0,
    "cached_bounds": {},   # tid -> (bounds, timestamp)
    # Cached static background frame (outline + sclera, no pupils).
    "_base_cache_key": None,
    "_base_cache_val": None,
    # Spin animation: pupil orbits eye center on left-click.
    "spin_phases": {},     # (tray_id, eye_idx) -> float t (0→1)
    "spin_tween_ids": {},  # (tray_id, eye_idx) -> tween_id
    "spin_params": {},     # (tray_id, eye_idx) -> (start_angle, rotations)
    # Upload rate limiter: cap tray_set_image calls during cursor tracking.
    "last_upload_at": {},  # tid -> float (monotonic)
}

# Blink animation duration in ms. Curve: rise(25%) → hold(45%) → fall(30%).
_BLINK_DURATION_MS = 320

# Spin animation: 2 full orbits over 700ms with ease_in_out (slow → fast → slow).
_SPIN_DURATION_MS = 700
_SPIN_ROTATIONS = 2

# Minimum seconds between tray_set_image uploads during cursor tracking (25 Hz).
# Spin bypasses this cap so interactive animation stays fluid.
_MIN_UPLOAD_INTERVAL_S = 0.040

# Sub-pixel movement threshold: skip tray icon rebuild when offsets haven't changed.
_RENDER_THRESHOLD = 0.4

# Exponential smoothing time constant for pupil position (ms).
# Lower = snappier follow; higher = more lag.
_SMOOTH_TC_MS = 80.0

# Cache TTLs (seconds) for FFI calls that change infrequently.
_CFG_TTL = 1.0       # re-read tokens once per second
_SCREEN_TTL = 5.0    # screen size almost never changes
_BOUNDS_TTL = 2.0    # tray icon position changes rarely


# ─── Cached FFI accessors ─────────────────────────────────────────────────────

def _cfg_cached():
    now = time.monotonic()
    if _state["cached_cfg"] is None or now - _state["cached_cfg_at"] >= _CFG_TTL:
        _state["cached_cfg"] = _load_config()
        _state["cached_cfg_at"] = now
    return _state["cached_cfg"]


def _screen_cached():
    now = time.monotonic()
    if _state["cached_screen"] is None or now - _state["cached_screen_at"] >= _SCREEN_TTL:
        _state["cached_screen"] = arcadia.screen_size(EXT)
        _state["cached_screen_at"] = now
    return _state["cached_screen"]


def _bounds_cached(tid):
    now = time.monotonic()
    entry = _state["cached_bounds"].get(tid)
    if entry is None or now - entry[1] >= _BOUNDS_TTL:
        bounds = arcadia.tray_icon_screen_bounds(EXT, tid)
        _state["cached_bounds"][tid] = (bounds, now)
        return bounds
    return entry[0]


def _invalidate_caches():
    _state["cached_cfg"] = None
    _state["cached_screen"] = None
    _state["cached_bounds"].clear()
    _state["_base_cache_key"] = None
    _state["_base_cache_val"] = None


# ─── Tray management ──────────────────────────────────────────────────────────

def _cancel_all_spin_tweens():
    for tween_id in list(_state["spin_tween_ids"].values()):
        try:
            arcadia.cancel_animation(tween_id)
        except Exception:
            pass
    _state["spin_tween_ids"].clear()
    _state["spin_phases"].clear()
    _state["spin_params"].clear()


def _cancel_all_blink_tweens():
    for tween_id in list(_state["blink_tween_ids"].values()):
        try:
            arcadia.cancel_animation(tween_id)
        except Exception:
            pass
    _state["blink_tween_ids"].clear()


def _sync_trays(cfg):
    separate = cfg["separate_eyes"]
    n = cfg["eye_count"] if separate else 1
    key = (separate, n)
    if _state["tray_layout_key"] == key and len(_state["tray_ids"]) == n:
        # Verify IDs are still registered — they may have been removed on extension disable.
        if all(arcadia.tray_item_registered(EXT, tid) for tid in _state["tray_ids"]):
            _apply_left_click_menu_policy(cfg)
            return
        # IDs are stale; fall through to re-register.
        _state["tray_ids"] = []
        _state["tray_layout_key"] = None
    for tid in _state["tray_ids"]:
        try:
            arcadia.tray_remove(EXT, tid)
        except Exception:
            pass
    _state["tray_ids"] = []
    _state["eye_offsets"].clear()
    _state["blink_amounts"].clear()
    _state["held_wink_keys"] = set()
    _state["last_rendered"].clear()
    _cancel_all_spin_tweens()
    _cancel_all_blink_tweens()
    for i in range(n):
        if separate and n > 1:
            label = f"{MODULE_LABEL} ({i + 1})"
            tip = f"Googly eye {i + 1} of {n}"
        else:
            label = MODULE_LABEL
            tip = "Googly Eyes"
        if separate and n > 1:
            tid = arcadia.tray_register(EXT, label, tip, str(i))
        else:
            tid = arcadia.tray_register(EXT, label, tip)
        _state["tray_ids"].append(tid)
    _state["tray_layout_key"] = key
    _invalidate_caches()
    _apply_left_click_menu_policy(cfg)


def _apply_left_click_menu_policy(cfg):
    # Spin fires on every left-click, so always suppress the menu on left-click.
    for tid in _state["tray_ids"]:
        try:
            arcadia.tray_set_show_menu_on_left_click(EXT, tid, False)
        except Exception:
            pass


def _tray_center_x(tid):
    g = arcadia.tray_icon_screen_bounds(EXT, tid)
    if not g or len(g) < 4:
        return 0.0
    tx, _, tw, _ = g[0], g[1], g[2], g[3]
    return float(tx) + float(tw) * 0.5


# ─── Blink animation ──────────────────────────────────────────────────────────

def _blink_curve(t):
    """Map linear t → blink amount. Rise 0→1 in first 25%, hold, fall 1→0 in last 30%."""
    if t < 0.25:
        return t / 0.25
    elif t < 0.70:
        return 1.0
    else:
        return 1.0 - (t - 0.70) / 0.30


def _trigger_blink_on(tray_id, eye_idx):
    """Start a blink animation for one eye, cancelling any in-progress blink."""
    key = (tray_id, eye_idx)

    old = _state["blink_tween_ids"].pop(key, None)
    if old is not None:
        try:
            arcadia.cancel_animation(old)
        except Exception:
            pass

    def on_tick(t):
        amt = _blink_curve(t)
        _state["blink_amounts"][key] = amt
        # Clean up when animation ends naturally.
        if t >= 1.0:
            _state["blink_amounts"].pop(key, None)
            _state["blink_tween_ids"].pop(key, None)

    tween_id = arcadia.animate(EXT, _BLINK_DURATION_MS, "linear", on_tick)
    _state["blink_tween_ids"][key] = tween_id


def _wink_keys_for_button(button, cfg):
    """Return the set of (tray_id, eye_idx) pairs that should wink for this button."""
    keys = set()
    if not (cfg["blink_on_click"] or cfg["relative_blink_on_click"]):
        return keys
    if button not in ("left", "right"):
        return keys

    rel = cfg["relative_blink_on_click"] and cfg["eye_count"] >= 2
    n = cfg["eye_count"]

    if cfg["separate_eyes"]:
        tids = list(_state["tray_ids"])
        if not tids:
            return keys
        if rel and len(tids) >= 2:
            ranked = sorted(((t, _tray_center_x(t)) for t in tids), key=lambda p: p[1])
            target_tid = ranked[0][0] if button == "left" else ranked[-1][0]
            keys.add((target_tid, 0))
        else:
            for t in tids:
                keys.add((t, 0))
        return keys

    if not _state["tray_ids"]:
        return keys
    cid = _state["tray_ids"][0]
    if rel:
        eye_idx = 0 if button == "left" else n - 1
        keys.add((cid, eye_idx))
    else:
        for i in range(n):
            keys.add((cid, i))
    return keys


def _trigger_blink_fall(key):
    """Animate blink_amount for one eye from its current value → 0 (release phase only)."""
    old = _state["blink_tween_ids"].pop(key, None)
    if old is not None:
        try:
            arcadia.cancel_animation(old)
        except Exception:
            pass
    start = _state["blink_amounts"].get(key, 1.0)

    def on_tick(t):
        _state["blink_amounts"][key] = _lerp_f(start, 0.0, t)
        if t >= 1.0:
            _state["blink_amounts"].pop(key, None)
            _state["blink_tween_ids"].pop(key, None)

    tween_id = arcadia.animate(EXT, 96, "ease_out_cubic", on_tick)
    _state["blink_tween_ids"][key] = tween_id


def _trigger_blink(button, cfg):
    if not (cfg["blink_on_click"] or cfg["relative_blink_on_click"]):
        return
    if button not in ("left", "right"):
        return

    rel = cfg["relative_blink_on_click"] and cfg["eye_count"] >= 2
    n = cfg["eye_count"]

    if cfg["separate_eyes"]:
        tids = list(_state["tray_ids"])
        if not tids:
            return
        if rel and len(tids) >= 2:
            ranked = sorted(((t, _tray_center_x(t)) for t in tids), key=lambda p: p[1])
            target_tid = ranked[0][0] if button == "left" else ranked[-1][0]
            _trigger_blink_on(target_tid, 0)
        else:
            for t in tids:
                _trigger_blink_on(t, 0)
        return

    if not _state["tray_ids"]:
        return
    cid = _state["tray_ids"][0]
    if rel:
        eye_idx = 0 if button == "left" else n - 1
        _trigger_blink_on(cid, eye_idx)
    else:
        for i in range(n):
            _trigger_blink_on(cid, i)


def _trigger_spin_on(tray_id, eye_indices, cfg):
    """Orbit each pupil around its eye center. Multiple eyes get unique phase/speed."""
    max_offset = max(0.0, cfg["eye_r"] - cfg["pupil_r"] - cfg["outline"])
    if max_offset <= 0:
        return
    n = len(eye_indices)
    for slot, eye_idx in enumerate(eye_indices):
        key = (tray_id, eye_idx)
        old = _state["spin_tween_ids"].pop(key, None)
        if old is not None:
            try:
                arcadia.cancel_animation(old)
            except Exception:
                pass
        _state["spin_phases"].pop(key, None)

        # Each eye gets a unique starting angle and rotation count so they
        # orbit independently rather than in lockstep.
        if n > 1:
            start_angle = slot * (2 * math.pi / n)
            rotations = _SPIN_ROTATIONS + slot * 0.5
        else:
            start_angle = 0.0
            rotations = float(_SPIN_ROTATIONS)
        _state["spin_params"][key] = (start_angle, rotations, max_offset)

        def _make_cb(k, tid):
            def on_tick(t):
                _state["spin_phases"][k] = t
                if t >= 1.0:
                    params = _state["spin_params"].pop(k, None)
                    _state["spin_phases"].pop(k, None)
                    _state["spin_tween_ids"].pop(k, None)
                    # Seed eye_offsets with a random angle so each eye
                    # settles from a unique position when lerping back to cursor.
                    if params is not None:
                        _, _, s_max = params
                        exit_angle = random.uniform(0, 2 * math.pi)
                        _state["eye_offsets"][k] = (
                            s_max * math.cos(exit_angle),
                            s_max * math.sin(exit_angle),
                        )
                    _state["last_rendered"].pop(tid, None)
            return on_tick

        tween_id = arcadia.animate(EXT, _SPIN_DURATION_MS, "ease_out_cubic", _make_cb(key, tray_id))
        _state["spin_tween_ids"][key] = tween_id


def _on_tray_click(tray_id, button):
    if button != "left":
        return
    cfg = _load_config()
    if cfg["separate_eyes"]:
        _trigger_spin_on(tray_id, [0], cfg)
    else:
        _trigger_spin_on(tray_id, list(range(cfg["eye_count"])), cfg)


# ─── Tick loop ────────────────────────────────────────────────────────────────

def _blink_snapshot(tid, eye_count):
    """Return a dict of just the blink amounts relevant to this tray id + eye count."""
    return {
        (tid, i): _state["blink_amounts"].get((tid, i), 0.0)
        for i in range(eye_count)
    }


def _needs_render(tid, smooth, blink_snap):
    """Return True if the tray icon must be redrawn."""
    if any(k[0] == tid for k in _state["spin_phases"]):
        return True
    last = _state["last_rendered"].get(tid)
    if last is None:
        return True
    last_smooth, last_blink = last
    if len(last_smooth) != len(smooth):
        return True
    if any(
        abs(a[0] - b[0]) + abs(a[1] - b[1]) > _RENDER_THRESHOLD
        for a, b in zip(last_smooth, smooth)
    ):
        return True
    return last_blink != blink_snap


def _smooth_offsets_for_icon(cfg, tray_id, eye_centers, width, height, geom, cursor_pt, screen_wh, alpha):
    """Update and return smooth eye offsets for one tray icon."""
    targets = _pupil_target_offsets(cfg, width, height, eye_centers, geom, cursor_pt, screen_wh)
    result = []
    for i, (tx, ty) in enumerate(targets):
        key = (tray_id, i)
        cur = _state["eye_offsets"].get(key, (tx, ty))
        nx = _lerp_f(cur[0], tx, alpha)
        ny = _lerp_f(cur[1], ty, alpha)
        _state["eye_offsets"][key] = (nx, ny)
        result.append((nx, ny))
    return result


def _tick():
    try:
        cfg = _cfg_cached()
        _sync_trays(cfg)

        want_blink = cfg["blink_on_click"] or cfg["relative_blink_on_click"]
        if not want_blink:
            _state["mouse_left_prev"] = False
            _state["mouse_right_prev"] = False

        cursor = None
        if want_blink:
            snap = arcadia.cursor_snapshot(EXT)
            if snap:
                cx, cy, ld, rd = snap
                cursor = (cx, cy)
                held_left  = _wink_keys_for_button("left",  cfg) if ld else set()
                held_right = _wink_keys_for_button("right", cfg) if rd else set()
                desired_held = held_left | held_right
                prev_held = _state["held_wink_keys"]

                for key in desired_held - prev_held:
                    old = _state["blink_tween_ids"].pop(key, None)
                    if old is not None:
                        try:
                            arcadia.cancel_animation(old)
                        except Exception:
                            pass
                    _state["blink_amounts"][key] = 1.0

                for key in desired_held:
                    _state["blink_amounts"][key] = 1.0

                for key in prev_held - desired_held:
                    _trigger_blink_fall(key)

                _state["held_wink_keys"] = desired_held
                _state["mouse_left_prev"]  = ld
                _state["mouse_right_prev"] = rd
            else:
                prev_held = _state["held_wink_keys"]
                for key in prev_held:
                    _trigger_blink_fall(key)
                _state["held_wink_keys"] = set()
                _state["mouse_left_prev"] = False
                _state["mouse_right_prev"] = False

        if cursor is None:
            cursor = arcadia.cursor_position(EXT)

        screen = _screen_cached()

        # Frame-rate-compensated smoothing factor: alpha = 1 - exp(-dt / tc)
        alpha = 1.0 - math.exp(-cfg["refresh_ms"] / _SMOOTH_TC_MS)

        now = time.monotonic()

        # Compute left/right roles for angled emotions (sorted by screen X, leftmost = True).
        angled_emotion = cfg.get("emotion") in ("sad", "angry")
        if angled_emotion and cfg["separate_eyes"] and len(_state["tray_ids"]) >= 2:
            ranked = sorted(_state["tray_ids"], key=lambda t: _tray_center_x(t))
            _sep_roles = {ranked[0]: True, ranked[-1]: False}
        else:
            _sep_roles = {}

        if cfg["separate_eyes"]:
            for i_slot, tid in enumerate(_state["tray_ids"]):
                eye_r, pupil_r, spacing, outline, eye_diameter, width, height, eye_centers = (
                    _eye_geometry(cfg, 1)
                )
                geom = _bounds_cached(tid)
                smooth = _smooth_offsets_for_icon(
                    cfg, tid, eye_centers, width, height, geom, cursor, screen, alpha
                )
                blink_snap = _blink_snapshot(tid, 1)
                spinning = any(k[0] == tid for k in _state["spin_phases"])
                if _needs_render(tid, smooth, blink_snap):
                    if spinning or now - _state["last_upload_at"].get(tid, 0.0) >= _MIN_UPLOAD_INTERVAL_S:
                        eye_roles = [_sep_roles[tid]] if (angled_emotion and tid in _sep_roles) else None
                        rgba, w, h = _render_rgba(
                            cfg, smooth, _state["blink_amounts"], tid, eye_centers, width, height, eye_roles
                        )
                        arcadia.tray_set_image(EXT, tid, rgba, w, h)
                        _state["last_rendered"][tid] = (list(smooth), blink_snap)
                        _state["last_upload_at"][tid] = now
        else:
            tid = _state["tray_ids"][0]
            eye_r, pupil_r, spacing, outline, eye_diameter, width, height, eye_centers = (
                _eye_geometry(cfg, cfg["eye_count"])
            )
            geom = _bounds_cached(tid)
            smooth = _smooth_offsets_for_icon(
                cfg, tid, eye_centers, width, height, geom, cursor, screen, alpha
            )
            blink_snap = _blink_snapshot(tid, cfg["eye_count"])
            spinning = any(k[0] == tid for k in _state["spin_phases"])
            if _needs_render(tid, smooth, blink_snap):
                if spinning or now - _state["last_upload_at"].get(tid, 0.0) >= _MIN_UPLOAD_INTERVAL_S:
                    # Non-separate: eye_centers ordered left→right by _eye_geometry construction.
                    eye_roles = [True, False] if angled_emotion else None
                    rgba, w, h = _render_rgba(
                        cfg, smooth, _state["blink_amounts"], tid, eye_centers, width, height, eye_roles
                    )
                    arcadia.tray_set_image(EXT, tid, rgba, w, h)
                    _state["last_rendered"][tid] = (list(smooth), blink_snap)
                    _state["last_upload_at"][tid] = now

    except Exception as e:
        print(f"googly-eyes tick error: {e}")


# ─── Commands ─────────────────────────────────────────────────────────────────

def _start_timer():
    cfg = _load_config()
    _invalidate_caches()
    if _state["timer_id"] is not None:
        arcadia.cancel_timer(_state["timer_id"])
    _state["timer_id"] = arcadia.set_timer(EXT, cfg["refresh_ms"], _tick)


def _cmd_reload(_args):
    _state["tray_layout_key"] = None
    _sync_trays(_load_config())
    _start_timer()
    return "Googly Eyes refresh timer restarted and tray layout synced."


def _cmd_hide(_args):
    if _state["timer_id"] is not None:
        arcadia.cancel_timer(_state["timer_id"])
        _state["timer_id"] = None
    _cancel_all_spin_tweens()
    _cancel_all_blink_tweens()
    for tid in list(_state["tray_ids"]):
        try:
            arcadia.tray_remove(EXT, tid)
        except Exception:
            pass
    _state["tray_ids"] = []
    _state["tray_layout_key"] = None
    _state["eye_offsets"].clear()
    _state["blink_amounts"].clear()
    _state["mouse_left_prev"] = False
    _state["mouse_right_prev"] = False
    _state["held_wink_keys"] = set()
    return "Googly Eyes hidden — re-enable the extension to bring them back."


arcadia.register_command(
    "googly-eyes.reload",
    "Re-read tokens and restart the googly-eyes refresh timer.",
    _cmd_reload,
)
arcadia.register_command(
    "googly-eyes.hide",
    "Remove the googly eyes tray icon and stop its refresh timer.",
    _cmd_hide,
)

arcadia.register_tray_icon_click_handler(EXT, _on_tray_click)

_sync_trays(_load_config())
_start_timer()
