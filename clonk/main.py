"""Clonk — mechanical keyboard sounds, as an Arcadia Python extension.

Listens to OS-global key/mouse/scroll events and triggers procedural DSP voices
(or sampled WAVs) through Arcadia's audio engine. All product semantics
(voice recipes, key→sound mapping, sample-pack conventions) live in Python; the
underlying `keyboard` and `audio` modules in ArcadiaCore are deliberately generic.

Settings live on the registered nav page — no tray icon in v1.
"""

import os
import sys
import json
import random

import arcadia

EXTENSION_ID = "clonk"

# Python host execs main.py via exec() with no __file__ set; siblings (voices.py,
# samplepack.py) aren't importable until we put the bundle dir on sys.path.
# extension_assets_path returns <bundle>/Assets; the parent is the bundle root.
_assets_dir = arcadia.extension_assets_path(EXTENSION_ID)
if _assets_dir:
    _bundle_dir = os.path.dirname(_assets_dir)
    if _bundle_dir not in sys.path:
        sys.path.insert(0, _bundle_dir)

# Evict stale cached modules so `python-host.reload` picks up edits to voices.py
# or samplepack.py without restarting Arcadia.
for _mod_name in list(sys.modules):
    if _mod_name in ("voices", "samplepack"):
        del sys.modules[_mod_name]

import voices as _voices  # noqa: E402
import samplepack as _samplepack  # noqa: E402

# ─── module registration ─────────────────────────────────────────────────────

arcadia.register_module(
    name=EXTENSION_ID,
    version="0.1.0",
    description="Mechanical keyboard sound simulator — procedural clicks, no bundled samples.",
    permissions=["keyboard.global_events", "audio.output"],
    platforms=["macos"],
    tags=["audio", "fun"],
)

# Token UI rendered on the nav page below.
arcadia.register_tokens(EXTENSION_ID, [
    {"key": "voice", "label": "Voice", "kind": "string", "default": "blue",
     "options": ["blue", "brown", "red", "deep_thock", "vintage_typewriter", "sample_pack"]},
    {"key": "volume", "label": "Volume", "kind": "float", "default": 0.7,
     "min": 0.0, "max": 1.0, "granularity": "thousandth"},
    {"key": "release_click", "label": "Play release clicks", "kind": "bool", "default": True},
    {"key": "mouse_clicks", "label": "Play on mouse buttons", "kind": "bool", "default": True},
    {"key": "scroll_ticks", "label": "Play on scroll wheel", "kind": "bool", "default": False},
    {"key": "muted", "label": "Mute", "kind": "bool", "default": False},
    {"key": "sample_pack_dir", "label": "Sample pack directory (WAV)", "kind": "string",
     "default": "", "visible_when": {"token": "voice", "eq": "sample_pack"}},
])


# ─── voice registration ──────────────────────────────────────────────────────
#
# Each named voice in voices.VOICES is registered once with the audio engine and
# its returned voice id cached. Per-keystroke we look up the active voice token
# and trigger the cached id — registration is the slow part, triggering is hot.

_voice_ids = {}  # voice_name → audio voice id


def _register_voices():
    for name, graph in _voices.VOICES.items():
        try:
            vid = arcadia.audio_register_voice(EXTENSION_ID, json.dumps(graph))
            _voice_ids[name] = vid
        except Exception as e:
            print(f"clonk: failed to register voice '{name}': {e}")


_register_voices()


# ─── settings cache ──────────────────────────────────────────────────────────
#
# read_tokens hits a TOML file; caching avoids that on every keystroke. The token
# change handler below refreshes the cache and reloads the sample pack if the
# directory token changed.

_settings = {}


def _as_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v) if v is not None else default


def _as_float(v, default=0.0):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return default
    return default


def _as_str(v, default=""):
    return v if isinstance(v, str) else (str(v) if v is not None else default)


def _refresh_settings():
    """read_tokens returns the display-string form for every token; coerce here so
    every consumer sees real Python bools / floats / strs.
    """
    try:
        raw = dict(arcadia.read_tokens(EXTENSION_ID))
    except Exception as e:
        print(f"clonk: read_tokens failed: {e}")
        return
    _settings.clear()
    _settings["voice"] = _as_str(raw.get("voice"), "blue")
    _settings["volume"] = _as_float(raw.get("volume"), 0.7)
    _settings["release_click"] = _as_bool(raw.get("release_click"), True)
    _settings["mouse_clicks"] = _as_bool(raw.get("mouse_clicks"), True)
    _settings["scroll_ticks"] = _as_bool(raw.get("scroll_ticks"), False)
    _settings["muted"] = _as_bool(raw.get("muted"), False)
    _settings["sample_pack_dir"] = _as_str(raw.get("sample_pack_dir"), "")


_refresh_settings()
arcadia.audio_set_master_gain(EXTENSION_ID, _settings.get("volume", 0.7))


def _on_tokens_changed(_new_tokens):
    # `_new_tokens` carries the raw display-string form. Always re-read through
    # the typed coercion path so downstream code never branches on stringy values.
    prev_dir = _settings.get("sample_pack_dir", "")
    _refresh_settings()
    try:
        arcadia.audio_set_master_gain(EXTENSION_ID, _settings.get("volume", 0.7))
    except Exception as e:
        print(f"clonk: set_master_gain failed: {e}")
    new_dir = _settings.get("sample_pack_dir", "")
    if new_dir != prev_dir or (
        _settings.get("voice") == "sample_pack" and _samplepack.loaded_dir() != new_dir
    ):
        _samplepack.load_pack(EXTENSION_ID, new_dir)


arcadia.register_token_change_handler(EXTENSION_ID, _on_tokens_changed)


# ─── event handler ───────────────────────────────────────────────────────────


def _trigger(velocity):
    if _settings.get("muted", False):
        return
    voice_name = _settings.get("voice", "blue")
    if voice_name == "sample_pack":
        # Caller decides which event kind; this branch is taken from _on_event.
        return
    vid = _voice_ids.get(voice_name)
    if not vid:
        return
    try:
        arcadia.audio_play_voice(EXTENSION_ID, vid, velocity, random.randint(1, 2_000_000_000))
    except Exception as e:
        # Don't spam logs at typing rate — only complain on permission revocation
        # so a mid-session toggle of audio.output is visible to the user.
        if "Permission" in str(e):
            print(f"clonk: audio gate closed: {e}")


def _trigger_sample(kind, gain):
    sid = _samplepack.pick(kind)
    if not sid:
        return
    try:
        # Slight pitch variation makes repeats feel less mechanical.
        pitch = 1.0 + random.uniform(-0.03, 0.03)
        arcadia.audio_play_sample(EXTENSION_ID, sid, gain, pitch)
    except Exception as e:
        if "Permission" in str(e):
            print(f"clonk: audio gate closed: {e}")


def _on_event(ev):
    if _settings.get("muted", False):
        return
    kind = ev.get("kind")
    sample_mode = _settings.get("voice") == "sample_pack"

    if kind == "KeyDown":
        if ev.get("repeat", False):
            return
        if sample_mode:
            _trigger_sample("keydown", 1.0)
        else:
            _trigger(0.85)
    elif kind == "KeyUp":
        if not _settings.get("release_click", True):
            return
        if sample_mode:
            _trigger_sample("keyup", 0.7)
        else:
            _trigger(0.45)
    elif kind in ("MouseDown", "MouseUp"):
        if not _settings.get("mouse_clicks", True):
            return
        if sample_mode:
            _trigger_sample("mousedown" if kind == "MouseDown" else "mouseup", 0.9)
        else:
            _trigger(0.7)
    elif kind == "ScrollWheel":
        if not _settings.get("scroll_ticks", False):
            return
        if sample_mode:
            _trigger_sample("scroll", 0.7)
        else:
            _trigger(0.35)


arcadia.keyboard_on_event(EXTENSION_ID, _on_event)


# ─── commands ────────────────────────────────────────────────────────────────


def _cmd_status(_args):
    voice = _settings.get("voice", "blue")
    muted = _settings.get("muted", False)
    state = "muted" if muted else voice
    if voice == "sample_pack":
        n = _samplepack.total_loaded()
        state = f"sample_pack ({n} samples)" if not muted else "muted"
    return state


def _cmd_mute(_args):
    # Mutes by setting the token (so the UI updates too). Use the audio panic to
    # cut any sound already in-flight.
    cur = arcadia.read_tokens(EXTENSION_ID) or {}
    new_muted = not bool(cur.get("muted", False))
    cur["muted"] = new_muted
    _settings["muted"] = new_muted
    # Best-effort persist via token write (handled by core extension_tokens config).
    try:
        arcadia.audio_panic(EXTENSION_ID)
    except Exception:
        pass
    return "muted" if new_muted else "unmuted"


def _cmd_panic(_args):
    try:
        arcadia.audio_panic(EXTENSION_ID)
        return "All voices stopped."
    except Exception as e:
        return f"panic failed: {e}"


def _cmd_reload_pack(_args):
    n = _samplepack.load_pack(EXTENSION_ID, _settings.get("sample_pack_dir", ""))
    return f"Loaded {n} samples."


arcadia.register_command(f"{EXTENSION_ID}.status", "Current voice / muted state.", _cmd_status)
arcadia.register_command(f"{EXTENSION_ID}.mute", "Toggle mute.", _cmd_mute)
arcadia.register_command(f"{EXTENSION_ID}.panic", "Stop all currently playing voices.", _cmd_panic)
arcadia.register_command(
    f"{EXTENSION_ID}.reload_pack", "Re-scan the configured sample-pack directory.", _cmd_reload_pack
)


# Settings UI is auto-rendered from register_tokens above (settings-hub card).
# Commands above (clonk.mute / clonk.panic / clonk.reload_pack) remain available
# via the CLI and `arcadia.execute(...)`.

# If the user already configured a pack and selected sample-pack mode, load it now.
if _settings.get("voice") == "sample_pack" and _settings.get("sample_pack_dir"):
    _samplepack.load_pack(EXTENSION_ID, _settings["sample_pack_dir"])
