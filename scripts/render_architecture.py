"""Render architecture.png from the v6 diagram. No Cloud Run box as host."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture.png"

W, H = 1600, 1000
BG = (16, 20, 15)
INK = (239, 230, 207)
AMBER = (212, 90, 18)
LINE = (203, 189, 154)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("arialbd.ttf", "arial.ttf", "C:\\Windows\\Fonts\\arialbd.ttf", "C:\\Windows\\Fonts\\arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def box(draw: ImageDraw.ImageDraw, xy, title: str, sub: str, fill=None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=10, outline=INK, width=3, fill=fill or (28, 34, 26))
    draw.text((x0 + 16, y0 + 12), title, font=font(22), fill=AMBER)
    draw.text((x0 + 16, y0 + 44), sub, font=font(16), fill=INK)


def arrow(draw, a, b):
    draw.line([a, b], fill=LINE, width=3)


def main() -> None:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((48, 28), "tmc-gate  ·  Coast Range TMC  ·  not Cloud Run", font=font(28), fill=INK)
    d.text((48, 68), "FIRMS CSV+KML  →  Pub/Sub  →  BQ ST_Intersects + EE NASADEM + Gemini quotes  →  stdlib MATCH", font=font(18), fill=LINE)

    box(d, (48, 130, 430, 250), "FIRMS 24h CSV+KML", "no MAP_KEY  ·  not EE FIRMS", (36, 28, 18))
    box(d, (480, 130, 860, 250), "Pub/Sub batches", "poller → BQ load + EE task")
    box(d, (910, 130, 1280, 250), "TOM Ch 110 PDF", "Gemini quote-or-refuse")
    box(d, (1330, 130, 1560, 250), "Model Armor", "fail-closed")

    box(d, (48, 320, 620, 460), "BigQuery ST_Intersects", "native VIIRS footprint ∩ D5 SHN")
    box(d, (680, 320, 1240, 460), "Earth Engine NASADEM", "z_hotspot > z_shn   delete EE → cannot MATCH")

    box(d, (200, 520, 1400, 660), "stdlib  MATCH | NON-MATCH | CAN'T READ", "LLM never returns MATCH   ·   county-only MUST fail", (48, 22, 14))

    box(d, (48, 720, 520, 900), "Firestore TMCAL", "OPEN → CLOSED_FIRE\nHCRR draft  write_happened")
    box(d, (560, 720, 1040, 900), "HTTPS /reopen/{route}/{pm}", "REFUSE | ALLOW  ·  product URL\n/conformance 3/3")
    box(d, (1080, 720, 1560, 900), "Cloud Functions + Storage", "host  ·  /judges stepper\nNOT .run.app")

    d.text((48, 940), "404 unreachable: traveler-info, CAD, cones, blast, FEMA, email, Cloud Run host", font=font(16), fill=LINE)
    im.save(OUT, "PNG")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
