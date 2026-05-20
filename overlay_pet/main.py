"""overlay-pet — desktop HUD companion (bottom-right).

Requires modules: `python-host`, `overlay`. Permission: `overlay.hud`.

Pet kinds: token `pet_kind` (string). Supported: `cat`, `gray-cat`.
Unknown kind falls back to `cat`.
Sprite: 360×200 RGBA procedural.
"""

from __future__ import annotations

import os
import sys
from typing import Callable

import arcadia

EXT = "overlay-pet"

# ── Import resolution ─────────────────────────────────────────────────────────
# The Python host loads main.py via exec() with no __file__ set.
# arcadia.extension_assets_path returns <bundle>/Assets; its parent is the
# bundle root where draw.py and the pets/ package live.
_assets_dir = arcadia.extension_assets_path(EXT)
if _assets_dir:
    _bundle_dir = os.path.dirname(_assets_dir)
    if _bundle_dir not in sys.path:
        sys.path.insert(0, _bundle_dir)

# Evict stale cached modules so `python-host.reload` picks up edits.
for _mod_name in list(sys.modules):
    if _mod_name in ("draw", "pets", "pets.cat", "pets.gray_cat"):
        del sys.modules[_mod_name]

from draw import W, H  # noqa: E402
from pets.cat import render_cat  # noqa: E402
from pets.gray_cat import render_gray_cat  # noqa: E402

# ── Pet registry ──────────────────────────────────────────────────────────────

PET_RENDERERS: dict[str, Callable[[], bytes]] = {
    "cat": render_cat,
    "gray-cat": render_gray_cat,
}


def _pet_kind() -> str:
    raw = (arcadia.read_tokens(EXT) or {}).get("pet_kind") or "cat"
    s = str(raw).strip().lower()
    return s if s else "cat"


def render_pet(kind: str) -> bytes:
    fn = PET_RENDERERS.get(kind)
    return fn() if fn is not None else render_cat()


# ── Overlay push ──────────────────────────────────────────────────────────────

_state: dict = {
    "cached_key": None,  # (kind, pr, pb, dw, dh)
    "cached_rgba": None,
}


def _display_params(tok: dict) -> tuple:
    pr = float(tok.get("pad_right") or 24)
    pb = float(tok.get("pad_bottom") or 24)
    ds = float(tok["display_size"]) if tok.get("display_size") is not None else None
    return pr, pb, ds


def _push_overlay(force: bool = False) -> None:
    kind = _pet_kind()
    tok = arcadia.read_tokens(EXT) or {}
    pr, pb, ds = _display_params(tok)
    cache_key = (kind, pr, pb, ds)
    if not force and cache_key == _state["cached_key"] and _state["cached_rgba"] is not None:
        return
    rgba = render_pet(kind)
    _state["cached_key"] = cache_key
    _state["cached_rgba"] = rgba
    arcadia.overlay_hud_set_sprite(EXT, rgba, W, H, stacking="hud", pad_right=pr, pad_bottom=pb, display_width=ds, display_height=(ds * H / W) if ds is not None else None)
    arcadia.execute("overlay.show", [])


# ── Commands ──────────────────────────────────────────────────────────────────

def _on_token_change(_tokens) -> str:
    _state["cached_key"] = None
    _push_overlay(force=True)
    return f"overlay-pet: refreshed (pet_kind={_pet_kind()!r})."


def _cmd_hide(_args) -> str:
    try:
        arcadia.overlay_hud_clear_sprite(EXT)
    except Exception:
        pass
    arcadia.execute("overlay.hide", [])
    return "overlay-pet: sprite cleared and overlay hidden."


# ── Registration ──────────────────────────────────────────────────────────────

arcadia.register_module(
    name=EXT,
    version="0.4.0",
    description="Bottom-right HUD pet (desktop overlay).",
    permissions=["overlay.hud"],
    platforms=["macos", "windows", "linux"],
    tags=["stable", "overlay"],
)

arcadia.register_tokens(
    EXT,
    [
        {
            "key": "pet_kind",
            "label": "Pet type",
            "kind": "string",
            "default": "cat",
            "options": ["cat", "gray-cat"],
        },
        {
            "key": "pad_right",
            "label": "Padding from right (px)",
            "kind": "float",
            "default": 24.0,
        },
        {
            "key": "pad_bottom",
            "label": "Padding from bottom (px)",
            "kind": "float",
            "default": 24.0,
        },
        {
            "key": "display_size",
            "label": "Display size (pt)",
            "kind": "float",
            "default": 180.0,
            "min": 40.0,
            "max": 600.0,
        },
    ],
)

arcadia.register_token_change_handler(EXT, _on_token_change)
arcadia.register_command(
    "overlay-pet.hide",
    "Clear sprite and hide the overlay window.",
    _cmd_hide,
)

_push_overlay()
