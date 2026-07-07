#!/usr/bin/env python3
"""
Remove white (or near-white) background from an image and save as PNG.

Uses edge-connected flood fill so only background white pixels are made
transparent — interior white regions (e.g. letters inside a logo) are
preserved.

Usage:
    python remove-bg.py --input PATH [--output PATH] [--threshold 240]

Inputs:
    --input      : Path to source image (JPG, PNG, BMP, WEBP, etc.) (required)
    --output     : Output PNG path (optional; defaults to <name>_nobg.png
                   in ~/Downloads)
    --threshold  : 0–255, minimum R/G/B value considered "white" (default 240)
                   Lower = removes more shades; higher = only pure white

Outputs:
    Saves a PNG with transparent background.
    Prints JSON to stdout: {input, output, size, status}

Exit codes:
    0 — success
    1 — input error (file not found, bad args)
    2 — processing error
"""

import argparse
import json
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow",
          file=sys.stderr)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Remove white background from an image and save as PNG"
    )
    p.add_argument("--input",     required=True,  help="Source image path")
    p.add_argument("--output",    default="",     help="Output PNG path (optional)")
    p.add_argument("--threshold", type=int, default=240,
                   help="Min R/G/B value considered white (0–255, default 240)")
    return p.parse_args()


def flood_fill_bg_mask(img: Image.Image, threshold: int) -> list[list[bool]]:
    """
    BFS from all edge pixels to find background white pixels.
    Returns a 2D mask (width x height): True = background pixel to remove.
    """
    width, height = img.size
    pixels = img.load()
    visited = [[False] * height for _ in range(width)]
    mask    = [[False] * height for _ in range(width)]
    queue: deque[tuple[int, int]] = deque()

    def is_white(x: int, y: int) -> bool:
        px = pixels[x, y]
        r, g, b = px[0], px[1], px[2]
        return r >= threshold and g >= threshold and b >= threshold

    # Seed queue from all four edges
    for x in range(width):
        for y_edge in (0, height - 1):
            if not visited[x][y_edge] and is_white(x, y_edge):
                visited[x][y_edge] = True
                mask[x][y_edge]    = True
                queue.append((x, y_edge))
    for y in range(height):
        for x_edge in (0, width - 1):
            if not visited[x_edge][y] and is_white(x_edge, y):
                visited[x_edge][y] = True
                mask[x_edge][y]    = True
                queue.append((x_edge, y))

    # BFS — expand to 4-connected white neighbours
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height \
                    and not visited[nx][ny] and is_white(nx, ny):
                visited[nx][ny] = True
                mask[nx][ny]    = True
                queue.append((nx, ny))

    return mask


def remove_bg(input_path: str, output_path: str, threshold: int) -> dict:
    src = Path(input_path)
    if not src.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    img = Image.open(src).convert("RGBA")
    mask = flood_fill_bg_mask(img, threshold)

    width, height = img.size
    pixels = img.load()
    for x in range(width):
        for y in range(height):
            if mask[x][y]:
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)

    out = Path(output_path) if output_path else \
          Path.home() / "Downloads" / f"{src.stem}_nobg.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG")

    return {
        "input":     str(src.resolve()),
        "output":    str(out.resolve()),
        "size":      f"{width}x{height}",
        "threshold": threshold,
        "status":    "saved",
    }


def main() -> None:
    args = parse_args()

    if not 0 <= args.threshold <= 255:
        print("Error: --threshold must be between 0 and 255", file=sys.stderr)
        sys.exit(1)

    try:
        result = remove_bg(args.input, args.output, args.threshold)
        print(json.dumps(result, indent=2))
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
