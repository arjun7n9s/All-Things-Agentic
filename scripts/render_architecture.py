"""Render architecture.png for Devpost — Gemini → ADK → Functions → data → desk UI."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "architecture.png"

W, H = 1800, 1180
BG = (11, 11, 12)
INK = (232, 230, 227)
AMBER = (217, 119, 6)
GREEN = (34, 120, 70)
RED = (196, 48, 43)
BLUE = (56, 110, 168)
PANEL = (18, 18, 20)
LINE = (55, 55, 58)
MUTED = (139, 134, 128)
SOFT = (28, 28, 32)


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


def box(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    title: str,
    sub: str,
    *,
    fill=PANEL,
    outline=INK,
    title_fill=AMBER,
):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=6, outline=outline, width=2, fill=fill)
    draw.text((x0 + 14, y0 + 12), title, font=font(18), fill=title_fill)
    for i, line in enumerate(sub.split("\n")):
        draw.text((x0 + 14, y0 + 40 + i * 20), line, font=font(14), fill=INK)


def lane(draw: ImageDraw.ImageDraw, y0: int, y1: int, label: str):
    draw.rectangle((24, y0, W - 24, y1), outline=LINE, width=1, fill=SOFT)
    draw.text((36, y0 + 8), label, font=font(13), fill=MUTED)


def arrow_v(draw: ImageDraw.ImageDraw, x: int, y0: int, y1: int, label: str = ""):
    draw.line((x, y0, x, y1 - 8), fill=AMBER, width=2)
    draw.polygon([(x - 6, y1 - 10), (x + 6, y1 - 10), (x, y1)], fill=AMBER)
    if label:
        draw.text((x + 10, (y0 + y1) // 2 - 8), label, font=font(12), fill=MUTED)


def arrow_h(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, label: str = ""):
    draw.line((x0, y, x1 - 8, y), fill=AMBER, width=2)
    draw.polygon([(x1 - 10, y - 6), (x1 - 10, y + 6), (x1, y)], fill=AMBER)
    if label:
        draw.text(((x0 + x1) // 2 - 40, y - 22), label, font=font(12), fill=MUTED)


def main() -> None:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    d.text((40, 22), "Upslope · tmc-gate · Architecture", font=font(30), fill=INK)
    d.text(
        (40, 58),
        "Gemini quotes · stdlib decides MATCH · Cloud Functions host (not Cloud Run) · Firestore TMCAL SoR",
        font=font(15),
        fill=MUTED,
    )

    # —— Lane 1: External start guns ——
    lane(d, 95, 230, "1 · EXTERNAL INPUTS")
    box(
        d,
        (48, 120, 420, 215),
        "NOAA FIRMS 24h CSV + KML",
        "Live gun · no MAP_KEY\nNot EE FIRMS catalog",
        fill=(32, 24, 16),
        outline=AMBER,
    )
    box(
        d,
        (450, 120, 820, 215),
        "Cloud Scheduler",
        "Unattended overnight wake\nGET /wake?case=live",
        outline=BLUE,
        title_fill=BLUE,
    )
    box(
        d,
        (850, 120, 1220, 215),
        "TOM Ch 110 + PIO prose",
        "HCRR 10 min · county/route/PM\nSteep slope above highway",
        outline=MUTED,
        title_fill=MUTED,
    )
    box(
        d,
        (1250, 120, 1752, 215),
        "Judge / fixture TMC lead",
        "Browser → /judges · /reopen\ncurl · Devpost demo film",
        outline=INK,
    )

    arrow_v(d, 230, 215, 250, "")
    arrow_v(d, 635, 215, 250, "")
    arrow_v(d, 1500, 215, 250, "")

    # —— Lane 2: Frontend ——
    lane(d, 250, 400, "2 · FRONTEND  ·  dispatcher desk (static HTML + SSR first paint)")
    box(
        d,
        (48, 280, 560, 385),
        "Desk UI · /judges",
        "Frozen A / B · Live · 404 · conformance\nTypography-as-state · zero chat",
        fill=(22, 28, 36),
        outline=BLUE,
        title_fill=BLUE,
    )
    box(
        d,
        (590, 280, 1100, 385),
        "Product surfaces",
        "/health · /reopen/{route}/{pm}\n?format=cert · /conformance · /llms.txt",
        fill=(22, 28, 36),
        outline=BLUE,
        title_fill=BLUE,
    )
    box(
        d,
        (1130, 280, 1752, 385),
        "What the judge sees",
        "MATCH + three quotes + chips on first paint\nPOST /reopen/CA-1/PM12 → REFUSED",
        fill=(22, 28, 36),
        outline=BLUE,
        title_fill=BLUE,
    )

    arrow_v(d, 900, 385, 420, "HTTPS")

    # —— Lane 3: Backend host ——
    lane(d, 420, 560, "3 · BACKEND HOST  ·  Cloud Functions HTTP 2nd gen  ·  cloudfunctions.net")
    box(
        d,
        (48, 450, 700, 545),
        "tmc-gate  ·  entry: tmc_gate",
        "Flask / Functions Framework\n/wake · /reopen · /board · SSR /judges\nNOT advertised as .run.app",
        fill=(20, 32, 24),
        outline=GREEN,
        title_fill=GREEN,
    )
    box(
        d,
        (730, 450, 1200, 545),
        "Secret Manager + Model Armor",
        "ADC / secrets · fail-closed Armor\nArmor regional us-central1",
        fill=(40, 20, 20),
        outline=RED,
        title_fill=RED,
    )
    box(
        d,
        (1230, 450, 1752, 545),
        "Pub/Sub witness",
        "firms-batches · firms-ee-tasks\nWake publish after MATCH write",
        outline=MUTED,
        title_fill=MUTED,
    )

    arrow_v(d, 370, 545, 580, "tools")

    # —— Lane 4: Gemini / ADK ——
    lane(d, 580, 760, "4 · GEMINI + GOOGLE ADK  ·  quotes only · never returns MATCH")
    box(
        d,
        (48, 610, 620, 745),
        "Vertex AI · Gemini 3.7 Flash",
        "GOOGLE_CLOUD_LOCATION=global\novernight + quote → 3.7\n429 shed → gemini-3.5-flash\nlite probe → 3.1-flash-lite",
        fill=(20, 36, 28),
        outline=GREEN,
        title_fill=GREEN,
    )
    box(
        d,
        (650, 610, 1200, 745),
        "Google ADK",
        "LlmAgent (overnight parent)\nAgentTool (quote clerk)\nFunctionTools:\n  fetch → quote → join → write\n  → publish → probe_reopen",
        fill=(20, 36, 28),
        outline=GREEN,
        title_fill=GREEN,
    )
    box(
        d,
        (1230, 610, 1752, 745),
        "Quote-or-refuse",
        "TOM / PIO / FIRMS verbatim\nor CAN'T READ\nLLM text is never eval()'d\nMATCH is not a model output",
        fill=(28, 24, 18),
        outline=AMBER,
    )

    arrow_h(d, 620, 650, 675, "")
    arrow_h(d, 1200, 1230, 675, "quotes")
    arrow_v(d, 900, 745, 780, "attrs only")

    # —— Lane 5: Data / decision ——
    lane(d, 780, 980, "5 · DATA + DECISION PLANE  ·  stdlib conjunction (BQ ∩ EE ∩ confidence ∩ D5)")
    box(
        d,
        (48, 810, 480, 965),
        "BigQuery",
        "ST_Intersects(\n  VIIRS pixel, D5 SHN)\nNative scan×track ~375m\nNo invented 100-ft buffer",
        outline=BLUE,
        title_fill=BLUE,
    )
    box(
        d,
        (510, 810, 940, 965),
        "Earth Engine",
        "NASADEM\nz_hotspot > z_shn\nDelete EE → CAN'T MATCH\n(U7 kill if skipped)",
        outline=BLUE,
        title_fill=BLUE,
    )
    box(
        d,
        (970, 810, 1400, 965),
        "stdlib gate",
        "MATCH | NON-MATCH | CAN'T READ\nCounty-only MUST fail\nwrite_happened only on MATCH",
        fill=(48, 22, 14),
        outline=RED,
        title_fill=RED,
    )
    box(
        d,
        (1430, 810, 1752, 965),
        "Firestore TMCAL",
        "SoR\nOPEN → CLOSED_FIRE\nHCRR row\nreopen log",
        outline=GREEN,
        title_fill=GREEN,
    )

    arrow_h(d, 480, 510, 885, "")
    arrow_h(d, 940, 970, 885, "conjunct")
    arrow_h(d, 1400, 1430, 885, "write")

    # —— Lane 6: Outcomes ——
    lane(d, 990, 1120, "6 · MUTATION THE JUDGE WATCHES")
    box(
        d,
        (48, 1020, 560, 1105),
        "POST /reopen/CA-1/PM12",
        "REFUSED + three quotes\n?format=cert → hashes",
        fill=(40, 24, 14),
        outline=AMBER,
    )
    box(
        d,
        (590, 1020, 1100, 1105),
        "POST /reopen/CA-1/PM47",
        "ALLOWED after Frozen A\nNot a county webhook",
        fill=(18, 32, 22),
        outline=GREEN,
        title_fill=GREEN,
    )
    box(
        d,
        (1130, 1020, 1752, 1105),
        "GET /conformance → 3/3",
        "Scores Firestore objects — not Gemini prose\n404: traveler-info · CAD · email · Cloud Run host",
        outline=INK,
    )

    d.text(
        (40, 1140),
        "Track: Taskmaster · Gemini 3.5+ (primary 3.7) · Google ADK · Cloud Functions + Firestore + Pub/Sub + BigQuery + Earth Engine + Model Armor",
        font=font(13),
        fill=MUTED,
    )

    im.save(OUT, "PNG")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
