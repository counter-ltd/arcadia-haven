import subprocess
import json
import threading

import arcadia

EXTENSION_ID = "taurine"
_lock = threading.RLock()  # reentrant: _tick → _update_tray safe
_state = {
    "active": False,
    "seconds_remaining": 0,
    "indefinite": False,
    "active_seconds": 0,
    "process": None,
    "timer_id": None,
}
_tray_id = None
_icon_cache = None  # None = not yet attempted; False = failed; tuple = (bytes, w, h)

PRESETS = [
    ("15 min",  900),
    ("30 min",  1800),
    ("1 hour",  3600),
    ("2 hours", 7200),
    ("4 hours", 14400),
]


def _fmt(secs):
    h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
    return f"{h}h {m:02d}m" if h else f"{m}m {s:02d}s"


def _decode_png_rgba(data):
    import struct, zlib
    assert data[:8] == b'\x89PNG\r\n\x1a\n', "not PNG"
    pos, width, height, color_type, idats = 8, None, None, None, []
    while pos < len(data):
        length = struct.unpack_from('>I', data, pos)[0]
        ct = data[pos + 4:pos + 8]
        cd = data[pos + 8:pos + 8 + length]
        if ct == b'IHDR':
            width, height = struct.unpack_from('>II', cd)
            color_type = cd[9]
        elif ct == b'IDAT':
            idats.append(cd)
        elif ct == b'IEND':
            break
        pos += 12 + length
    bpp = 4 if color_type == 6 else 3
    raw = zlib.decompress(b''.join(idats))
    stride = width * bpp
    out = bytearray(width * height * 4)
    prev = bytearray(stride)

    def paeth(a, b, c):
        p = a + b - c
        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
        return a if pa <= pb and pa <= pc else (b if pb <= pc else c)

    for y in range(height):
        off = y * (stride + 1)
        ft = raw[off]
        row = bytearray(raw[off + 1:off + 1 + stride])
        if ft == 1:
            for x in range(bpp, stride):
                row[x] = (row[x] + row[x - bpp]) & 0xFF
        elif ft == 2:
            for x in range(stride):
                row[x] = (row[x] + prev[x]) & 0xFF
        elif ft == 3:
            for x in range(stride):
                a = row[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + (a + prev[x]) // 2) & 0xFF
        elif ft == 4:
            for x in range(stride):
                a = row[x - bpp] if x >= bpp else 0
                b_val = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + paeth(a, b_val, c)) & 0xFF
        row_out = y * width * 4
        if color_type == 6:
            out[row_out:row_out + width * 4] = row
        else:
            for x in range(width):
                out[row_out + x * 4:row_out + x * 4 + 3] = row[x * 3:x * 3 + 3]
                out[row_out + x * 4 + 3] = 255
        prev = row
    return bytes(out), width, height


def _load_icon_rgba(size=44):
    global _icon_cache
    if _icon_cache is not None:
        return _icon_cache if _icon_cache is not False else None
    result = None
    try:
        import cairosvg, io
        svg_data = arcadia.read_extension_asset(EXTENSION_ID, "icon.svg")
        png = cairosvg.svg2png(bytestring=svg_data, output_width=size, output_height=size)
        from PIL import Image
        img = Image.open(io.BytesIO(png)).convert("RGBA")
        result = (bytes(img.tobytes()), img.width, img.height)
    except Exception:
        pass
    if result is None:
        try:
            import os, tempfile, subprocess
            assets = arcadia.extension_assets_path(EXTENSION_ID)
            svg_path = os.path.join(assets, "icon.svg")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            try:
                subprocess.run(
                    ["sips", "-z", str(size), str(size), "-s", "format", "png", svg_path, "--out", tmp],
                    check=True, capture_output=True, timeout=5,
                )
                with open(tmp, "rb") as f:
                    rgba, w, h = _decode_png_rgba(f.read())
                px = bytearray(rgba)
                for i in range(0, len(px), 4):
                    px[i] = px[i + 1] = px[i + 2] = 255
                result = (bytes(px), w, h)
            finally:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
        except Exception as e:
            print(f"[taurine] icon load failed: {e}")
    _icon_cache = result if result is not None else False
    return result


def _register_tray():
    global _tray_id
    if _tray_id is not None:
        return
    try:
        _tray_id = arcadia.tray_register(EXTENSION_ID, "☕", "Taurine — Preventing sleep")
    except Exception as e:
        print(f"[taurine] tray_register failed: {e}")
        return
    try:
        arcadia.tray_set_show_menu_on_left_click(EXTENSION_ID, _tray_id, True)
        icon = _load_icon_rgba()
        if icon:
            rgba, w, h = icon
            arcadia.tray_set_image(EXTENSION_ID, _tray_id, rgba, w, h)
    except Exception as e:
        print(f"[taurine] tray setup failed: {e}")


def _remove_tray():
    global _tray_id
    if _tray_id is None:
        return
    try:
        arcadia.tray_remove(EXTENSION_ID, _tray_id)
    except Exception:
        pass
    _tray_id = None


def _build_menu(active, remaining=0, indefinite=False):
    items = []
    if active:
        status = "Indefinite" if indefinite else _fmt(remaining)
        items.append({"label": status, "command": "", "args": []})
        items.append({"separator": True})
    for label, secs in PRESETS:
        items.append({"label": label, "command": "taurine.start", "args": [str(secs)]})
    items.append({"label": "Indefinitely", "command": "taurine.start", "args": ["-1"]})
    if active:
        items.append({"separator": True})
        items.append({"label": "Stop", "command": "taurine.stop", "args": []})
    return items


def _update_tray():
    if _tray_id is None:
        return
    try:
        with _lock:
            active = _state["active"]
            remaining = _state["seconds_remaining"]
            indefinite = _state["indefinite"]
        if active:
            tip = f"Taurine — Awake {'indefinitely' if indefinite else _fmt(remaining)}"
        else:
            tip = "Taurine — Sleep enabled"
        arcadia.tray_set_tooltip(EXTENSION_ID, _tray_id, tip)
        arcadia.tray_set_menu(EXTENSION_ID, _tray_id, _build_menu(active, remaining, indefinite))
    except Exception:
        pass


def _do_stop():
    with _lock:
        proc = _state.get("process")
        timer = _state.get("timer_id")
        _state["active"] = False
        _state["seconds_remaining"] = 0
        _state["indefinite"] = False
        _state["active_seconds"] = 0
        _state["process"] = None
        _state["timer_id"] = None
    if proc:
        try:
            proc.terminate()
        except Exception:
            pass
    if timer is not None:
        try:
            arcadia.cancel_timer(timer)
        except Exception:
            pass
    _remove_tray()


def _tick():
    expired = False
    with _lock:
        if not _state["active"] or _state["indefinite"]:
            pass
        else:
            _state["seconds_remaining"] -= 1
            if _state["seconds_remaining"] <= 0:
                expired = True
    if expired:
        _do_stop()
    else:
        _update_tray()


def handle_start(args):
    secs = int(args[0]) if args else 3600
    indefinite = secs < 0
    _do_stop()
    cmd = ["caffeinate", "-d", "-i", "-m", "-s"]
    if not indefinite:
        cmd += ["-t", str(secs)]
    try:
        proc = subprocess.Popen(cmd)
    except Exception as e:
        return json.dumps({"error": str(e)})
    timer_id = arcadia.set_timer(EXTENSION_ID, 1000, _tick)
    with _lock:
        _state["active"] = True
        _state["seconds_remaining"] = secs if not indefinite else 0
        _state["indefinite"] = indefinite
        _state["active_seconds"] = secs
        _state["process"] = proc
        _state["timer_id"] = timer_id
    _register_tray()
    _update_tray()
    return json.dumps({"ok": True})


def handle_stop(args):
    _do_stop()
    return json.dumps({"ok": True})


def handle_status(args):
    with _lock:
        active = _state["active"]
        remaining = _state["seconds_remaining"]
        indefinite = _state["indefinite"]
        active_seconds = _state["active_seconds"]
    if active:
        text = "Awake indefinitely" if indefinite else f"Active — {_fmt(remaining)}"
    else:
        text = "Inactive"
    active_args = [str(active_seconds)] if active else None
    return json.dumps({"text": text, "active": active, "active_args": active_args})


# Registration
arcadia.register_module(
    EXTENSION_ID,
    "1.0.0",
    "Prevent system sleep for a set duration.",
    permissions=["tray.create"],
    platforms=["macos"],
    tags=["stable", "tray"],
)

arcadia.register_command(
    "taurine.start",
    "Prevent sleep for N seconds (-1 = indefinite)",
    handle_start,
)
arcadia.register_command(
    "taurine.stop",
    "Re-enable system sleep",
    handle_stop,
)
arcadia.register_command(
    "taurine.status",
    "JSON: {text, active}",
    handle_status,
)

arcadia.register_nav_page(
    EXTENSION_ID,
    "utilities",
    title="Taurine",
    description="Prevent system sleep for a set duration.",
    glyph="extension-icon/taurine",
    system_image="bolt",
    accent="amber",
    status_command="taurine.status",
    actions=[
        {"label": "15 min",       "command": "taurine.start", "args": ["900"],   "style": "secondary"},
        {"label": "30 min",       "command": "taurine.start", "args": ["1800"],  "style": "secondary"},
        {"label": "1 hour",       "command": "taurine.start", "args": ["3600"],  "style": "secondary"},
        {"label": "2 hours",      "command": "taurine.start", "args": ["7200"],  "style": "secondary"},
        {"label": "4 hours",      "command": "taurine.start", "args": ["14400"], "style": "secondary"},
        {"label": "Indefinitely", "command": "taurine.start", "args": ["-1"],    "style": "secondary"},
        {"label": "Stop",         "command": "taurine.stop",  "args": [],        "style": "destructive"},
    ],
)

