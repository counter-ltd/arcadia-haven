"""Sample-pack loader for clonk.

A sample pack is a directory of WAV files following a simple naming convention:

    keydown.wav | keydown_01.wav … keydown_NN.wav      → key-down sounds
    keyup.wav   | keyup_01.wav   … keyup_NN.wav        → key-up (release) sounds
    mousedown.wav | mousedown_01.wav …                 → mouse-button down
    mouseup.wav   | mouseup_01.wav   …                 → mouse-button up
    scroll.wav    | scroll_01.wav    …                 → scroll wheel ticks

When multiple files match an event kind, one is picked at random per trigger.
Anything that doesn't match is ignored.
"""

import os
import random
import re
import arcadia

EVENT_KINDS = ("keydown", "keyup", "mousedown", "mouseup", "scroll")

# event_kind → list[sample_id]
_loaded = {k: [] for k in EVENT_KINDS}
_loaded_dir = None


def _is_match(filename, kind):
    stem = os.path.splitext(filename)[0].lower()
    if stem == kind:
        return True
    return bool(re.fullmatch(rf"{kind}_\d+", stem))


def load_pack(extension_id, directory):
    """Scan `directory` for WAVs, load each via audio_load_sample, store ids."""
    global _loaded_dir
    unload(extension_id)
    _loaded_dir = directory
    if not directory or not os.path.isdir(directory):
        return 0

    total = 0
    for entry in sorted(os.listdir(directory)):
        if not entry.lower().endswith(".wav"):
            continue
        path = os.path.join(directory, entry)
        for kind in EVENT_KINDS:
            if _is_match(entry, kind):
                try:
                    sid = arcadia.audio_load_sample(extension_id, path)
                    _loaded[kind].append(sid)
                    total += 1
                except Exception as e:
                    print(f"clonk: failed to load {path}: {e}")
                break
    return total


def unload(extension_id):
    """Drop every cached sample id, asking the engine to release the buffer."""
    global _loaded_dir
    for kind, ids in _loaded.items():
        for sid in ids:
            try:
                arcadia.audio_unload_sample(extension_id, sid)
            except Exception:
                pass
        _loaded[kind] = []
    _loaded_dir = None


def pick(kind):
    """Random sample id for the given event kind, or None if none loaded."""
    pool = _loaded.get(kind, [])
    if not pool:
        return None
    return random.choice(pool)


def loaded_dir():
    return _loaded_dir


def total_loaded():
    return sum(len(v) for v in _loaded.values())
