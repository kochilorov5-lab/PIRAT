from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
BASE = Image.open(ROOT / "pirat.png").convert("RGBA")


def downscale_hq(im: Image.Image, size: int) -> Image.Image:
    cur = im
    while cur.width > size * 2:
        cur = cur.resize((cur.width // 2, cur.height // 2), Image.Resampling.BOX)
    out = cur.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 32:
        alpha = out.getchannel("A")
        colored = ImageEnhance.Contrast(out.convert("RGB")).enhance(1.2)
        colored = ImageEnhance.Color(colored).enhance(1.1)
        out = colored.convert("RGBA")
        out.putalpha(alpha)
        sharp = out.filter(ImageFilter.UnsharpMask(radius=1.0, percent=120, threshold=2))
        out = Image.composite(sharp, out, alpha)
    return out


def make_mini(size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = max(1, size // 16)
    d.ellipse((pad, pad, size - 1 - pad, size - 1 - pad), fill=(91, 188, 228, 255))
    d.ellipse((size * 0.18, size * 0.18, size * 0.82, size * 0.52), fill=(28, 55, 92, 255))
    d.rectangle((size * 0.22, size * 0.34, size * 0.78, size * 0.42), fill=(232, 188, 70, 255))
    d.ellipse((size * 0.22, size * 0.38, size * 0.78, size * 0.88), fill=(230, 92, 48, 255))
    d.ellipse((size * 0.38, size * 0.58, size * 0.62, size * 0.72), fill=(255, 255, 255, 255))
    d.ellipse((size * 0.28, size * 0.42, size * 0.46, size * 0.58), fill=(20, 20, 24, 255))
    d.ellipse((size * 0.54, size * 0.44, size * 0.66, size * 0.56), fill=(20, 20, 24, 255))
    if size >= 20:
        d.ellipse((size * 0.57, size * 0.46, size * 0.61, size * 0.50), fill=(255, 255, 255, 255))
    return im


def png_bytes(im: Image.Image) -> bytes:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    # PNG-compressed ICO entries only — safer for PyInstaller / Explorer.
    plan = [
        (16, "mini"),
        (24, "mini"),
        (32, "hq"),
        (48, "hq"),
        (64, "hq"),
        (128, "hq"),
        (256, "hq"),
    ]
    entries: list[tuple[int, int, bytes, int]] = []
    for size, kind in plan:
        im = make_mini(size) if kind == "mini" else downscale_hq(BASE, size)
        data = png_bytes(im)
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        entries.append((w, h, data, size))

    header = struct.pack("<HHH", 0, 1, len(entries))
    offset = 6 + 16 * len(entries)
    directory = b""
    blob = b""
    for w, h, data, _size in entries:
        directory += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(data), offset)
        blob += data
        offset += len(data)

    out = ROOT / "pirat.ico"
    out.write_bytes(header + directory + blob)
    print(f"wrote {out} ({out.stat().st_size} bytes, {len(entries)} entries)")


if __name__ == "__main__":
    main()
