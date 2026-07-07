---
name: image-bg-remover
description: >-
  Removes white or near-white backgrounds from an image and saves the result
  as a transparent PNG. Use this when the user provides an image file and asks
  to remove the background, make the background transparent, strip the white
  background, or save as PNG without background.
argument-hint: "path to the image file (e.g. C:\\Users\\...\\logo.jpg)"
user-invocable: true
allowed-tools:
  - shell
---

# Image Background Remover

Removes white (or near-white) backgrounds from any image and saves it as a
transparent PNG. Uses edge-connected flood fill so only the outer background
is removed — interior white areas (e.g. text inside a logo) are preserved.

## Use When

- User provides an image and asks to remove the white background
- User wants to make the background transparent
- User wants to save an image as PNG with no background
- User has a logo or icon on a white background they want to clean up

## Prerequisites

- Python 3.10+ available
- Pillow installed: `pip install Pillow`

## Bundled Resources

- `./scripts/remove-bg.py` — background removal script

## Workflow Steps

### Step 1 — Get the image path

Ask the user:
> "What is the path to the image file?"

If the user already provided it, use that path directly.

### Step 2 — Check Pillow is installed

Run:
```
pip show Pillow
```

If not installed, run `pip install Pillow` before proceeding.

### Step 3 — Ask about threshold (optional)

Ask only if the user's image has an off-white or light grey background:
> "The default threshold is 240 (removes near-white pixels). Would you like
> to adjust it? Lower = removes more shades; higher = only pure white."

Use the default (240) unless the user specifies otherwise.

### Step 4 — Run the script

```
python ./scripts/remove-bg.py --input "<image-path>" [--threshold N] [--output "<output-path>"]
```

- Output defaults to `~/Downloads/<filename>_nobg.png` if `--output` is omitted.
- Add `--output` only if the user requests a specific save location.

### Step 5 — Report to the user

On success, report:
```
Done! Saved to: <output path>
  Original: <WxH>
  Threshold used: <N>
```

If the result looks wrong (e.g. too much or too little removed), suggest adjusting
`--threshold`:
- Background still visible → lower the threshold (e.g. `--threshold 220`)
- Too much removed → raise the threshold (e.g. `--threshold 250`)

## Examples

### Basic — remove white background from a logo

**User:** "Remove the background from C:\\Users\\sean\\logo.jpg"

```
python ./scripts/remove-bg.py --input "C:\\Users\\sean\\logo.jpg"
```

**Output:**
```json
{
  "input":     "C:\\Users\\sean\\logo.jpg",
  "output":    "C:\\Users\\sean\\Downloads\\logo_nobg.png",
  "size":      "800x600",
  "threshold": 240,
  "status":    "saved"
}
```

### Custom threshold — off-white background

**User:** "The background is light grey, not pure white"

```
python ./scripts/remove-bg.py --input "C:\\Users\\sean\\badge.png" --threshold 200
```

### Custom output path

```
python ./scripts/remove-bg.py \
  --input "C:\\Users\\sean\\logo.jpg" \
  --output "C:\\Users\\sean\\Desktop\\logo_transparent.png"
```

## Output Format

- A `.png` file with transparent background saved to the specified or default path
- JSON summary printed to stdout with `input`, `output`, `size`, `threshold`, `status`

## Completion Checklist

- [ ] Output file exists at the reported path
- [ ] Output is a `.png` file
- [ ] Background pixels are transparent (alpha = 0)
- [ ] Interior white regions (if any) are preserved
- [ ] User informed of the output path
