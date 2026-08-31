"""Render architecture.png — Gemini 3.5 + ADK + GCP. Not Cloud Run as host."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture.png"

W, H = 1680, 1080
BG = (11, 11, 12)
INK = (232, 230, 227)
AMBER = (217, 119, 6)
GREEN = (21, 128, 61)
RED = (220, 38, 38)
LINE = (42, 42, 44)
MUTED = (139, 134, 128)


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "arialbd.ttf",
        "arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def box(draw: ImageDraw.ImageDraw, xy, title: str, sub: str, fill=None, outline=None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=4, outline=outline or INK, width=2, fill=fill or (18, 18, 20))
    draw.text((x0 + 14, y0 + 12), title, font=font(20), fill=AMBER)
    for i, line in enumerate(sub.split("\n")):
        draw.text((x0 + 14, y0 + 42 + i * 22), line, font=font(15), fill=INK)


def main() -> None:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((40, 24), "tmc-gate · Coast Range TMC · Taskmaster", font=font(28), fill=INK)
    d.text(
        (40, 60),
        "Mandatory stack: Gemini 3.7 Flash routed (Vertex AI) · Google ADK (LlmAgent + AgentTool) · GCP (Functions, Firestore, Pub/Sub, BQ, EE, Armor)",
        font=font(16),
        fill=MUTED,
    )

    box(d, (40, 110, 400, 230), "FIRMS 24h CSV+KML", "live gun · no MAP_KEY\nnot EE FIRMS catalog", (28, 20, 14))
    box(d, (430, 110, 790, 230), "Cloud Scheduler", "unattended overnight wake\n?source=scheduler")
    box(d, (820, 110, 1180, 230), "Pub/Sub", "firms-batches\nfirms-ee-tasks")
    box(d, (1210, 110, 1640, 230), "Model Armor", "fail-closed sanitize\nus-central1 template", (40, 18, 18), RED)

    box(
        d,
        (40, 270, 820, 430),
        "Google ADK · Gemini 3.7 Flash (routed)",
        "Vertex AI location=global\novernight+quote → 3.7 · quote_retry → 3.5\nFunctionTools: fetch → quote → join → write → publish → reopen",
        (20, 32, 22),
        GREEN,
    )
    box(
        d,
        (860, 270, 1640, 430),
        "Quote-or-refuse (never MATCH)",
        "TOM Ch 110 + PIO upslope span\nFIRMS acq_time / confidence / FRP / sat\nLLM text is never eval'd for MATCH",
        (20, 28, 36),
    )

    box(d, (40, 470, 820, 620), "BigQuery ST_Intersects", "native VIIRS footprint ∩ D5 SHN\nno invented 100-ft buffer")
    box(d, (860, 470, 1640, 620), "Earth Engine NASADEM", "z_hotspot > z_shn (upslope)\ndelete EE → cannot MATCH")

    box(
        d,
        (200, 660, 1480, 780),
        "stdlib gate · MATCH | NON-MATCH | CAN'T READ",
        "three independent conjuncts · county-only MUST fail · write_happened only after MATCH",
        (48, 22, 14),
        RED,
    )

    box(d, (40, 820, 520, 980), "Firestore TMCAL SoR", "OPEN → CLOSED_FIRE\nHCRR row · reopen log")
    box(
        d,
        (560, 820, 1100, 980),
        "Product URL",
        "POST /reopen/{route}/{pm}\nREFUSED | ALLOWED · ?format=cert\n/conformance 3/3",
    )
    box(
        d,
        (1140, 820, 1640, 980),
        "Cloud Functions HTTP",
        "host: cloudfunctions.net\nNOT advertised .run.app\n/judges · /health desk",
    )

    d.text(
        (40, 1010),
        "404 unreachable: traveler-info · CAD · cones · blast · facility-reopen · email · Cloud Run host",
        font=font(15),
        fill=MUTED,
    )
    im.save(OUT, "PNG")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
