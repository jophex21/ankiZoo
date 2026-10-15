"""Renders sprite char-grids (see sprite_templates.py) to inline SVG data URIs.

Using SVG instead of a JS canvas renderer keeps the pixel art crisp with no
anti-aliasing (hard-edged <rect> per pixel) and lets idle animation be as
simple as swapping an <img src> between two precomputed frames on a timer.
"""
from __future__ import annotations

import base64
import mimetypes
from typing import Dict, List

OUTLINE_COLOR = "#1a1a1a"


def render_svg(frame: List[str], palette: Dict[str, str], pixel_size: int = 8) -> str:
    if not frame:
        return ""
    h = len(frame)
    w = len(frame[0])
    color_map = {
        "B": palette.get("B", "#cccccc"),
        "S": palette.get("S", "#aaaaaa"),
        "A": palette.get("A", "#888888"),
        "E": palette.get("E", "#111111"),
        "O": OUTLINE_COLOR,
    }

    rects = []
    for y, row in enumerate(frame):
        run_char = None
        run_start = None
        for x in range(w + 1):
            char = row[x] if x < w else None
            if char != run_char:
                if run_char is not None and run_char in color_map:
                    run_w = x - run_start
                    color = color_map[run_char]
                    rects.append(
                        f'<rect x="{run_start * pixel_size}" y="{y * pixel_size}" '
                        f'width="{run_w * pixel_size}" height="{pixel_size}" fill="{color}"/>'
                    )
                run_char = char
                run_start = x

    svg_w = w * pixel_size
    svg_h = h * pixel_size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}" shape-rendering="crispEdges">'
        f"{''.join(rects)}</svg>"
    )


def svg_data_uri(svg: str) -> str:
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def sprite_data_uri(frame: List[str], palette: Dict[str, str], pixel_size: int = 8) -> str:
    return svg_data_uri(render_svg(frame, palette, pixel_size))


def _build_fence_svg(size: int = 42, post: int = 3, gap: int = 4) -> str:
    """A dashed ring of small posts around the tile's perimeter (viewed top-down),
    transparent in the middle so the terrain/sprite show through underneath/above it.
    """
    body = "#a9752f"
    rects = []

    def add_post(x: int, y: int) -> None:
        rects.append(f'<rect x="{x}" y="{y}" width="{post}" height="{post}" fill="{OUTLINE_COLOR}"/>')
        rects.append(f'<rect x="{x + 1}" y="{y + 1}" width="{post - 2}" height="{post - 2}" fill="{body}"/>')

    step = post + gap
    x = 1
    while x + post <= size - 1:
        add_post(x, 0)
        add_post(x, size - post)
        x += step
    y = 1
    while y + post <= size - 1:
        add_post(0, y)
        add_post(size - post, y)
        y += step

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" shape-rendering="crispEdges">{"".join(rects)}</svg>'
    )


FENCE_DATA_URI = svg_data_uri(_build_fence_svg())


def file_data_uri(path: str) -> str:
    """Reads an image file from disk and returns it as a base64 data URI.

    Used for hand-authored sprite files (see animals.py's sprite folder
    lookup), kept alongside the procedural renderer above so both paths
    produce the same self-contained data-URI shape the webview expects.
    """
    mime, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime or 'application/octet-stream'};base64,{encoded}"


def scaled_png_data_uri(path: str, width: int) -> str:
    """Downscale an image to `width` px and return a PNG data URI.

    For large source art (e.g. the 2048px coin icon) that only ever renders a
    dozen pixels wide, so we don't inline the multi-MB original into every
    webview payload. Falls back to the raw file if Qt can't load it.
    """
    import os
    import tempfile
    from aqt.qt import QImage

    img = QImage(path)
    if img.isNull():
        return file_data_uri(path)
    scaled = img.scaledToWidth(width)  # default transform; browser resamples anyway
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        scaled.save(tmp, "PNG")
        with open(tmp, "rb") as f:
            data = f.read()
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
