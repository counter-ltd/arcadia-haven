"""Voice recipes for the clonk Python extension.

Each recipe is a JSON-compatible dict matching ArcadiaCore's audio voice-graph
schema. The five voices below port the synthesis parameters from clonk's native
Theme.swift to the generic DSP node primitives Arcadia exposes (noise_burst,
biquad bandpass, transient click, env_ar, mix). Tweak frequencies, Q, durations
here — no Rust rebuild required.

Schema reminder:
    {
      "nodes":  [{"id": str, "kind": ..., ...}, ...],
      "edges":  [[src_id, dst_id], ...],
      "output": str,
      "variations": {"freq_jitter_pct": float, "gain_jitter_pct": float}
    }

Available node kinds: noise_burst, biquad (bandpass|lowpass|highpass), transient,
env_ar, mix, gain.
"""


def _switch(
    *,
    noise_ms,
    bp1_hz,
    bp1_q,
    bp2_hz,
    bp2_q,
    transient_hz,
    transient_ms,
    release_ms,
    mix_gains,
    freq_jitter=2.5,
    gain_jitter=6.0,
):
    """Generic mechanical-switch graph builder. Two resonators sum with a high-
    passed transient click; an AR envelope shapes the tail.
    """
    return {
        "nodes": [
            {"id": "n",   "kind": "noise_burst", "duration_ms": noise_ms, "shape": "exp"},
            {"id": "bp1", "kind": "biquad", "mode": "bandpass", "freq_hz": bp1_hz, "q": bp1_q},
            {"id": "bp2", "kind": "biquad", "mode": "bandpass", "freq_hz": bp2_hz, "q": bp2_q},
            {"id": "tr",  "kind": "transient", "freq_hz": transient_hz, "duration_ms": transient_ms},
            {"id": "mx",  "kind": "mix", "gains": list(mix_gains)},
            {"id": "env", "kind": "env_ar", "attack_ms": 0.1, "release_ms": release_ms},
        ],
        "edges": [
            ["n", "bp1"], ["n", "bp2"],
            ["bp1", "mx"], ["bp2", "mx"], ["tr", "mx"],
            ["mx", "env"],
        ],
        "output": "env",
        "variations": {"freq_jitter_pct": freq_jitter, "gain_jitter_pct": gain_jitter},
    }


# Tactile + audible switch. Bright top resonance, sharp contact click.
BLUE = _switch(
    noise_ms=3.5, bp1_hz=420.0, bp1_q=14.0, bp2_hz=2900.0, bp2_q=7.0,
    transient_hz=7200.0, transient_ms=0.6, release_ms=70.0,
    mix_gains=(0.55, 0.35, 0.65),
)

# Tactile, less audible. Warmer body, softer transient.
BROWN = _switch(
    noise_ms=4.0, bp1_hz=320.0, bp1_q=12.0, bp2_hz=2200.0, bp2_q=6.0,
    transient_hz=5200.0, transient_ms=0.7, release_ms=85.0,
    mix_gains=(0.6, 0.3, 0.4),
)

# Smooth linear. No contact click, just the body resonance.
RED = _switch(
    noise_ms=4.5, bp1_hz=280.0, bp1_q=11.0, bp2_hz=1800.0, bp2_q=5.5,
    transient_hz=3800.0, transient_ms=0.4, release_ms=95.0,
    mix_gains=(0.65, 0.3, 0.15),
)

# Heavy, low-pitched "thock". Long body decay, minimal click.
DEEP_THOCK = _switch(
    noise_ms=5.5, bp1_hz=180.0, bp1_q=15.0, bp2_hz=900.0, bp2_q=8.0,
    transient_hz=3000.0, transient_ms=0.5, release_ms=140.0,
    mix_gains=(0.75, 0.45, 0.2),
    freq_jitter=1.8, gain_jitter=4.0,
)

# Vintage typewriter — bright, metallic, long ring.
VINTAGE_TYPEWRITER = _switch(
    noise_ms=3.0, bp1_hz=620.0, bp1_q=18.0, bp2_hz=3800.0, bp2_q=9.0,
    transient_hz=9200.0, transient_ms=0.9, release_ms=160.0,
    mix_gains=(0.4, 0.55, 0.85),
    freq_jitter=3.5, gain_jitter=8.0,
)


VOICES = {
    "blue":               BLUE,
    "brown":              BROWN,
    "red":                RED,
    "deep_thock":         DEEP_THOCK,
    "vintage_typewriter": VINTAGE_TYPEWRITER,
}
