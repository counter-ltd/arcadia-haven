"""Shared drawing primitives for overlay-pet sprites."""

from __future__ import annotations

import math

# Canvas dimensions — all renderers share the same sprite size.
W, H = 360, 200


def _blend(
    dst: tuple[int, int, int, int],
    src: tuple[int, int, int, int],
    a: float,
) -> tuple[int, int, int, int]:
    ar = src[3] / 255.0 * a
    inv = 1.0 - ar
    return (
        int(dst[0] * inv + src[0] * ar),
        int(dst[1] * inv + src[1] * ar),
        int(dst[2] * inv + src[2] * ar),
        min(255, int(dst[3] + src[3] * a)),
    )


def _composite(
    buf: bytearray,
    x: int,
    y: int,
    r: int,
    g: int,
    b: int,
    a: float,
) -> None:
    """Straight-alpha composite `a` in [0, 1] onto buffer."""
    if a < 0.002 or not (0 <= x < W and 0 <= y < H):
        return
    ai = min(255, max(0, int(round(a * 255))))
    if ai == 0:
        return
    i = (y * W + x) * 4
    dst = (buf[i], buf[i + 1], buf[i + 2], buf[i + 3])
    src = (r, g, b, ai)
    out = _blend(dst, src, 1.0)
    buf[i : i + 4] = out


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 1.0 if x >= edge1 else 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def _ellipse_aa(
    buf: bytearray,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    r: int,
    g: int,
    b: int,
    opacity: float = 1.0,
    feather: float = 0.045,
) -> None:
    """Axis-aligned ellipse, edge-antialiased."""
    if rx <= 0 or ry <= 0 or opacity <= 0:
        return
    x0 = max(0, int(cx - rx - 2))
    x1 = min(W, int(cx + rx + 3))
    y0 = max(0, int(cy - ry - 2))
    y1 = min(H, int(cy + ry + 3))
    inv_rx = 1.0 / max(rx, 0.01)
    inv_ry = 1.0 / max(ry, 0.01)
    for y in range(y0, y1):
        fy = y + 0.5 - cy
        dy = fy * inv_ry
        dy2 = dy * dy
        for x in range(x0, x1):
            fx = x + 0.5 - cx
            dx = fx * inv_rx
            d = math.sqrt(dx * dx + dy2)
            cover = 1.0 - _smoothstep(1.0 - feather, 1.0 + feather, d)
            if cover > 0:
                _composite(buf, x, y, r, g, b, cover * opacity)


def _ellipse_rot_aa(
    buf: bytearray,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    angle: float,
    r: int,
    g: int,
    b: int,
    opacity: float = 1.0,
    feather: float = 0.045,
) -> None:
    """Ellipse centered at (cx,cy), semi-axes rx/ry, rotated CCW by `angle` (radians)."""
    if rx <= 0 or ry <= 0 or opacity <= 0:
        return
    ca = math.cos(angle)
    sa = math.sin(angle)
    inv_rx = 1.0 / max(rx, 0.01)
    inv_ry = 1.0 / max(ry, 0.01)
    hw = math.hypot(rx * ca, ry * sa) + 2.5
    hh = math.hypot(rx * sa, ry * ca) + 2.5
    x0 = max(0, int(cx - hw))
    x1 = min(W, int(cx + hw + 1))
    y0 = max(0, int(cy - hh))
    y1 = min(H, int(cy + hh + 1))
    for y in range(y0, y1):
        fy = y + 0.5 - cy
        for x in range(x0, x1):
            fx = x + 0.5 - cx
            plx = fx * ca + fy * sa
            ply = -fx * sa + fy * ca
            dx = plx * inv_rx
            dy = ply * inv_ry
            d = math.sqrt(dx * dx + dy * dy)
            cover = 1.0 - _smoothstep(1.0 - feather, 1.0 + feather, d)
            if cover > 0:
                _composite(buf, x, y, r, g, b, cover * opacity)


def _fur_grain(buf: bytearray, ink_dark: tuple[int, int, int], ink_light: tuple[int, int, int]) -> None:
    """Sparse high-frequency variation on opaque pixels (reads as short fur at display scale)."""
    dr, dg, db = ink_dark
    lr, lg, lb = ink_light
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            i = (y * W + x) * 4
            if buf[i + 3] < 28:
                continue
            h = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
            if (h % 101) > 13:
                continue
            if (h >> 3) & 1:
                _composite(buf, x, y, dr, dg, db, 0.11 + (h & 7) * 0.01)
            else:
                _composite(buf, x, y, lr, lg, lb, 0.08 + (h & 5) * 0.008)


def _rosette(
    buf: bytearray,
    cx: float,
    cy: float,
    r_outer: float,
    r_mid: float,
    dark: tuple[int, int, int],
    light: tuple[int, int, int],
    angle: float = 0.0,
) -> None:
    """Leopard-style rosette: dark rim, warm center, slight rotation."""
    dr, dg, db = dark
    lr, lg, lb = light
    _ellipse_rot_aa(buf, cx, cy, r_outer, r_outer * 0.82, angle, dr, dg, db, 0.9, 0.048)
    _ellipse_rot_aa(buf, cx, cy + 0.5, r_mid, r_mid * 0.88, angle * 0.3, lr, lg, lb, 0.78, 0.055)
    ox = math.cos(angle) * r_outer * 0.32
    oy = math.sin(angle) * r_outer * 0.32
    _ellipse_aa(buf, cx - ox, cy - oy, r_outer * 0.22, r_outer * 0.18, lr, lg, lb, 0.52, 0.08)
    _ellipse_aa(buf, cx + ox * 0.9, cy - oy * 0.6, r_outer * 0.2, r_outer * 0.16, lr, lg, lb, 0.42, 0.09)


def _rim_darken(buf: bytearray, outline: tuple[int, int, int], strength: float = 0.24) -> None:
    """Darken pixels on the silhouette edge — gives sprite a grounded outline."""
    or_, og, ob = outline
    for y in range(H):
        for x in range(W):
            i = (y * W + x) * 4
            if buf[i + 3] == 0:
                continue
            edge = False
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = x + dx, y + dy
                if nx < 0 or ny < 0 or nx >= W or ny >= H or buf[(ny * W + nx) * 4 + 3] == 0:
                    edge = True
                    break
            if edge:
                cur = (buf[i], buf[i + 1], buf[i + 2], buf[i + 3])
                b_out = _blend(cur, (or_, og, ob, 255), strength)
                buf[i : i + 4] = b_out
