"""Render the macOS app icon into packaging/xRapture.iconset.

Draws the xRapture mic + waveform on a dark rounded-square tile at 1024px, then
downsamples to the standard iconset sizes. build_app.sh runs ``iconutil`` to turn
the iconset into xRapture.icns.
"""

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
WHITE = (255, 255, 255, 255)
RED = (226, 59, 46, 255)
BG = (32, 35, 42, 255)


def draw_design(draw: ImageDraw.ImageDraw, scale: float, ox: float, oy: float) -> None:
    """Plot the 64-unit mic/waveform design at the given scale and origin."""
    def pt(x, y):
        return (ox + x * scale, oy + y * scale)

    w = int(3 * scale)
    # mic capsule
    draw.rounded_rectangle([pt(26, 10), pt(38, 36)], radius=6 * scale, fill=WHITE)
    # cradle (bottom semicircle)
    draw.arc([pt(20, 18), pt(44, 42)], start=0, end=180, fill=WHITE, width=w)
    # stand + base
    draw.line([pt(32, 42), pt(32, 50)], fill=WHITE, width=w)
    draw.line([pt(24, 52), pt(40, 52)], fill=WHITE, width=w)
    # waveform bars (brand red)
    for x, half in ((10, 6), (15, 11), (49, 11), (54, 6)):
        draw.line([pt(x, 24 - half), pt(x, 24 + half)], fill=RED, width=w)


def render_master(size: int = 1024) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    inset = int(size * 0.08)
    draw.rounded_rectangle([inset, inset, size - inset, size - inset],
                           radius=int(size * 0.22), fill=BG)
    # Map the 64-unit design into the centre at ~69% of the tile.
    scale = size * 0.69 / 64
    origin = (size - 64 * scale) / 2
    draw_design(draw, scale, origin, origin)
    return img


def main() -> None:
    iconset = HERE / "xRapture.iconset"
    iconset.mkdir(exist_ok=True)
    master = render_master(1024)
    # (filename base, pixel size) pairs that iconutil expects
    specs = [
        ("icon_16x16", 16), ("icon_16x16@2x", 32),
        ("icon_32x32", 32), ("icon_32x32@2x", 64),
        ("icon_128x128", 128), ("icon_128x128@2x", 256),
        ("icon_256x256", 256), ("icon_256x256@2x", 512),
        ("icon_512x512", 512), ("icon_512x512@2x", 1024),
    ]
    for name, px in specs:
        master.resize((px, px), Image.LANCZOS).save(iconset / f"{name}.png")
    print(f"wrote {len(specs)} PNGs to {iconset}")


if __name__ == "__main__":
    main()
