import arcadia

arcadia.register_module(
    name="rainbow-indent",
    version="0.1.0",
    description="Translucent coloured boxes per indentation level.",
    tags=["stable", "code-editor"],
)

DEFAULTS = ["#e06c75", "#e5c07b", "#98c379", "#56b6c2", "#61afef", "#c678dd"]

arcadia.register_tokens("rainbow-indent",
    [
        {
            "key": f"level_{i + 1}",
            "label": f"Level {i + 1} colour",
            "kind": "color",
            "default": DEFAULTS[i],
        }
        for i in range(6)
    ] + [
        {
            "key": "opacity",
            "label": "Opacity (0–100)",
            "kind": "int",
            "default": 12,
            "min": 0,
            "max": 100,
            "granularity": "whole",
        }
    ]
)


def _hex_to_rgb(hex_str):
    h = hex_str.lstrip('#')
    if len(h) != 6:
        return (128, 128, 128)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def decorate(line, line_idx):
    spaces = len(line) - len(line.lstrip(' '))
    n_levels = spaces // 4
    if n_levels == 0:
        return []

    tokens = arcadia.read_tokens("rainbow-indent")
    try:
        opacity_pct = int(tokens.get("opacity", "12"))
    except ValueError:
        opacity_pct = 12
    alpha = max(0, min(255, int(opacity_pct / 100.0 * 255)))

    result = []
    for k in range(n_levels):
        level_key = f"level_{(k % 6) + 1}"
        hex_color = tokens.get(level_key, DEFAULTS[k % 6])
        r, g, b = _hex_to_rgb(hex_color)
        result.append({
            "col_start": k * 4,
            "col_width": 4,
            "r": r,
            "g": g,
            "b": b,
            "a": alpha,
        })
    return result


arcadia.register_editor_token_module("rainbow-indent")
arcadia.register_decoration_provider("rainbow-indent", decorate)
