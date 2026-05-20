import arcadia

arcadia.register_module(
    name="terminal-theme",
    version="0.1.0",
    description="Terminal render style — stroke+gap ━/┃ frame with full dark/light token coverage.",
    tags=["stable", "theme"],
)

arcadia.register_style(
    name="terminal",
    label="Terminal",
    description=(
        "Unicode dashed frame: horizontal ━ + space; vertical ┃ + gap — gaps use tight spacers (not full line height)."
    ),
    module="terminal-theme",
    bg="#0c0c0c",
    surface="#111111",
    surface2="#1a1a1a",
    text="#d4d4d4",
    dim="#555555",
    border="#333333",
    accent="#00cc88",
    light_bg="#f8fafc",
    light_surface="#ffffff",
    light_surface2="#f1f5f9",
    light_text="#0f172a",
    light_dim="#475569",
    light_border="#94a3b8",
    light_accent="#0f766e",
    border_chars="┏━┓┃┗━┛",
    border_radius=0.0,
    # Horizontal unchanged. Vertical ┃ + space: engine compresses whitespace rows so gaps match ━ + space density.
    border_horizontal_pattern="━ ",
    border_vertical_pattern="┃ ",
    # Optional typography overrides:
    # border_font_family="JetBrains Mono",
    # border_font_size_rems=0.75,
    # border_side_rail_px=11.0,
)

arcadia.register_tokens(
    "terminal-theme",
    [
        {"key": "bg_dark", "label": "Canvas (Dark)", "kind": "color", "default": "#0c0c0c"},
        {"key": "bg_light", "label": "Canvas (Light)", "kind": "color", "default": "#f8fafc"},
        {"key": "surface_dark", "label": "Surface (Dark)", "kind": "color", "default": "#111111"},
        {"key": "surface_light", "label": "Surface (Light)", "kind": "color", "default": "#ffffff"},
        {"key": "surface2_dark", "label": "Surface Elevated (Dark)", "kind": "color", "default": "#1a1a1a"},
        {"key": "surface2_light", "label": "Surface Elevated (Light)", "kind": "color", "default": "#f1f5f9"},
        {"key": "text_dark", "label": "Text (Dark)", "kind": "color", "default": "#d4d4d4"},
        {"key": "text_light", "label": "Text (Light)", "kind": "color", "default": "#0f172a"},
        {"key": "dim_dark", "label": "Dim (Dark)", "kind": "color", "default": "#555555"},
        {"key": "dim_light", "label": "Dim (Light)", "kind": "color", "default": "#475569"},
        {"key": "border_dark", "label": "Border (Dark)", "kind": "color", "default": "#333333"},
        {"key": "border_light", "label": "Border (Light)", "kind": "color", "default": "#94a3b8"},
        {"key": "accent_dark", "label": "Accent (Dark)", "kind": "color", "default": "#00cc88"},
        {"key": "accent_light", "label": "Accent (Light)", "kind": "color", "default": "#0f766e"},
        {"key": "border_chars_dark", "label": "Border Characters (Dark)", "kind": "string", "default": "┏━┓┃┗━┛"},
        {"key": "border_chars_light", "label": "Border Characters (Light)", "kind": "string", "default": "┏━┓┃┗━┛"},
        {"key": "border_horizontal_pattern_dark", "label": "Border Horizontal Pattern (Dark)", "kind": "string", "default": "━ "},
        {"key": "border_horizontal_pattern_light", "label": "Border Horizontal Pattern (Light)", "kind": "string", "default": "━ "},
        {"key": "border_vertical_pattern_dark", "label": "Border Vertical Pattern (Dark)", "kind": "string", "default": "┃ "},
        {"key": "border_vertical_pattern_light", "label": "Border Vertical Pattern (Light)", "kind": "string", "default": "┃ "},
        {"key": "ui_font_family_dark", "label": "UI Font Family (Dark)", "kind": "string", "default": ""},
        {"key": "ui_font_family_light", "label": "UI Font Family (Light)", "kind": "string", "default": ""},
        {"key": "border_font_family_dark", "label": "Border Font Family (Dark)", "kind": "string", "default": ""},
        {"key": "border_font_family_light", "label": "Border Font Family (Light)", "kind": "string", "default": ""},
        {"key": "border_font_size_rems_dark", "label": "Border Font Size Rems (Dark)", "kind": "float", "default": 0.75},
        {"key": "border_font_size_rems_light", "label": "Border Font Size Rems (Light)", "kind": "float", "default": 0.75},
        {"key": "border_side_rail_px_dark", "label": "Border Side Rail Px (Dark)", "kind": "float", "default": 11.0},
        {"key": "border_side_rail_px_light", "label": "Border Side Rail Px (Light)", "kind": "float", "default": 11.0},
        {"key": "border_radius_dark", "label": "Border Radius (Dark)", "kind": "float", "default": 0.0},
        {"key": "border_radius_light", "label": "Border Radius (Light)", "kind": "float", "default": 0.0},
    ],
)
