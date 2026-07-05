"""Procedural placeholder pixel-art generator.

Builds small char-grid "sprites" (later rendered to a <canvas> by
web/pixel_renderer.js) out of simple geometric primitives instead of
hand-authored bitmaps. This keeps 30 animals visually distinct without
needing real art, and is meant to be replaced by real sprite sheets later
(see animals.py: `sprite_file` overrides the procedural grid when present).
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple

GRID_W = 20
GRID_H = 20

Grid = List[List[str]]


def _make_grid(w: int = GRID_W, h: int = GRID_H, fill: str = ".") -> Grid:
    return [[fill for _ in range(w)] for _ in range(h)]


def _ellipse(grid: Grid, cx: float, cy: float, rx: float, ry: float, char: str) -> None:
    h = len(grid)
    w = len(grid[0])
    for y in range(h):
        for x in range(w):
            dx = (x - cx) / rx
            dy = (y - cy) / ry
            if dx * dx + dy * dy <= 1.0:
                grid[y][x] = char


def _rect(grid: Grid, x0: float, y0: float, x1: float, y1: float, char: str) -> None:
    h = len(grid)
    w = len(grid[0])
    for y in range(max(0, int(y0)), min(h, int(y1) + 1)):
        for x in range(max(0, int(x0)), min(w, int(x1) + 1)):
            grid[y][x] = char


def _outline(grid: Grid, char: str = "O") -> None:
    """Mark any empty cell orthogonally adjacent to a colored cell as outline."""
    h = len(grid)
    w = len(grid[0])
    to_mark = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] != ".":
                continue
            neighbors = [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
            for nx, ny in neighbors:
                if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] not in (".", char):
                    to_mark.append((x, y))
                    break
    for x, y in to_mark:
        grid[y][x] = char


def _base_blob(cx: float, cy: float, rx: float, ry: float) -> Grid:
    grid = _make_grid()
    _ellipse(grid, cx, cy, rx, ry, "B")
    # Belly/shade patch
    _ellipse(grid, cx, cy + ry * 0.35, rx * 0.55, ry * 0.4, "S")
    # Eyes
    eye_y = int(cy - ry * 0.15)
    eye_dx = int(rx * 0.35)
    grid[eye_y][int(cx - eye_dx)] = "E"
    grid[eye_y][int(cx + eye_dx)] = "E"
    return grid


def _template_mammal() -> Tuple[Grid, Grid]:
    cx, cy, rx, ry = GRID_W / 2 - 0.5, GRID_H * 0.56, GRID_W * 0.32, GRID_H * 0.34
    grid = _base_blob(cx, cy, rx, ry)
    # Round ears
    ear_r = GRID_W * 0.11
    _ellipse(grid, cx - rx * 0.6, cy - ry * 0.95, ear_r, ear_r, "B")
    _ellipse(grid, cx + rx * 0.6, cy - ry * 0.95, ear_r, ear_r, "B")
    # Feet
    _rect(grid, cx - rx * 0.5, cy + ry * 0.95, cx - rx * 0.15, cy + ry * 1.15, "B")
    _rect(grid, cx + rx * 0.15, cy + ry * 0.95, cx + rx * 0.5, cy + ry * 1.15, "B")
    blink = [row[:] for row in grid]
    eye_y = int(cy - ry * 0.15)
    eye_dx = int(rx * 0.35)
    blink[eye_y][int(cx - eye_dx)] = "B"
    blink[eye_y][int(cx + eye_dx)] = "B"
    _outline(grid)
    _outline(blink)
    return grid, blink


def _template_bird() -> Tuple[Grid, Grid]:
    cx, cy, rx, ry = GRID_W / 2 - 0.5, GRID_H * 0.52, GRID_W * 0.30, GRID_H * 0.32
    grid = _base_blob(cx, cy, rx, ry)
    # Beak
    _rect(grid, cx - rx * 0.18, cy + ry * 0.05, cx + rx * 0.18, cy + ry * 0.35, "A")
    # Wings
    _ellipse(grid, cx - rx * 0.95, cy + ry * 0.1, rx * 0.22, ry * 0.45, "S")
    _ellipse(grid, cx + rx * 0.95, cy + ry * 0.1, rx * 0.22, ry * 0.45, "S")
    # Feet
    _rect(grid, cx - rx * 0.3, cy + ry * 0.95, cx - rx * 0.1, cy + ry * 1.1, "A")
    _rect(grid, cx + rx * 0.1, cy + ry * 0.95, cx + rx * 0.3, cy + ry * 1.1, "A")
    blink = [row[:] for row in grid]
    eye_y = int(cy - ry * 0.15)
    eye_dx = int(rx * 0.35)
    blink[eye_y][int(cx - eye_dx)] = "B"
    blink[eye_y][int(cx + eye_dx)] = "B"
    _outline(grid)
    _outline(blink)
    return grid, blink


def _template_marine() -> Tuple[Grid, Grid]:
    cx, cy, rx, ry = GRID_W / 2 - 0.5, GRID_H * 0.55, GRID_W * 0.34, GRID_H * 0.30
    grid = _base_blob(cx, cy, rx, ry)
    # Dorsal fin
    _rect(grid, cx - rx * 0.1, cy - ry * 1.25, cx + rx * 0.1, cy - ry * 0.9, "S")
    # Flippers
    _ellipse(grid, cx - rx * 1.0, cy + ry * 0.5, rx * 0.28, ry * 0.28, "B")
    _ellipse(grid, cx + rx * 1.0, cy + ry * 0.5, rx * 0.28, ry * 0.28, "B")
    blink = [row[:] for row in grid]
    eye_y = int(cy - ry * 0.15)
    eye_dx = int(rx * 0.35)
    blink[eye_y][int(cx - eye_dx)] = "B"
    blink[eye_y][int(cx + eye_dx)] = "B"
    _outline(grid)
    _outline(blink)
    return grid, blink


def _template_biped() -> Tuple[Grid, Grid]:
    cx, cy, rx, ry = GRID_W / 2 - 0.5, GRID_H * 0.52, GRID_W * 0.26, GRID_H * 0.36
    grid = _base_blob(cx, cy, rx, ry)
    ear_r = GRID_W * 0.09
    _ellipse(grid, cx - rx * 0.65, cy - ry * 0.9, ear_r, ear_r, "B")
    _ellipse(grid, cx + rx * 0.65, cy - ry * 0.9, ear_r, ear_r, "B")
    # Arms
    _rect(grid, cx - rx * 1.25, cy - ry * 0.1, cx - rx * 0.95, cy + ry * 0.5, "B")
    _rect(grid, cx + rx * 0.95, cy - ry * 0.1, cx + rx * 1.25, cy + ry * 0.5, "B")
    # Feet
    _rect(grid, cx - rx * 0.45, cy + ry * 0.95, cx - rx * 0.1, cy + ry * 1.15, "B")
    _rect(grid, cx + rx * 0.1, cy + ry * 0.95, cx + rx * 0.45, cy + ry * 1.15, "B")
    blink = [row[:] for row in grid]
    eye_y = int(cy - ry * 0.15)
    eye_dx = int(rx * 0.35)
    blink[eye_y][int(cx - eye_dx)] = "B"
    blink[eye_y][int(cx + eye_dx)] = "B"
    _outline(grid)
    _outline(blink)
    return grid, blink


TEMPLATES = {
    "mammal": _template_mammal,
    "bird": _template_bird,
    "marine": _template_marine,
    "biped": _template_biped,
}


def _apply_pattern(grid: Grid, pattern: str, animal_id: str) -> Grid:
    """Recolor some 'B' cells to 'A' (accent) to differentiate animals sharing a template."""
    grid = [row[:] for row in grid]
    h = len(grid)
    w = len(grid[0])

    if pattern == "stripes":
        for x in range(w):
            if x % 3 == 0:
                for y in range(h):
                    if grid[y][x] == "B":
                        grid[y][x] = "A"
    elif pattern == "spots":
        seed = int(hashlib.sha1(animal_id.encode()).hexdigest(), 16)
        rng_state = seed
        count = 0
        attempts = 0
        while count < 7 and attempts < 200:
            attempts += 1
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            x = rng_state % w
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            y = rng_state % h
            if grid[y][x] == "B":
                grid[y][x] = "A"
                count += 1
    elif pattern == "mask":
        eye_rows = [y for y in range(h) if "E" in grid[y] or "B" in grid[y]]
        mid = h // 2
        for y in range(max(0, mid - 3), mid):
            for x in range(w):
                if grid[y][x] == "B":
                    grid[y][x] = "A"
    # "none" -> no-op

    return grid


def build_sprite_frames(template: str, pattern: str, animal_id: str) -> Tuple[Grid, Grid]:
    generator = TEMPLATES.get(template, _template_mammal)
    idle, blink = generator()
    idle = _apply_pattern(idle, pattern, animal_id)
    blink = _apply_pattern(blink, pattern, animal_id)
    return idle, blink


def grid_to_strings(grid: Grid) -> List[str]:
    return ["".join(row) for row in grid]
