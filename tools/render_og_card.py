#!/usr/bin/env python3
"""
Render the social-preview (Open Graph / Twitter) card for unpingable.

Produces ../og-card.png (1200x630) — the quiet branded card used in every
page's og:image / twitter:image. Edit the CARD constants below and re-run.

Design intent: postage-stamp legible. Wordmark + one essence line + author +
domain, one accent bar. No diagram, no small technical labels — social cards
are viewed thumbnail-sized by people who were not planning to attend a seminar.

Deps:  pip install pillow fonttools brotli
Usage: python3 tools/render_og_card.py
Notes: renders with Pillow (not headless chromium — chromium's --screenshot
       is unreliable in sandboxed/CI environments). Geist Mono is fetched from
       jsdelivr and converted woff2 -> ttf in a temp dir so Pillow can read it.
       Keep both repo copies of og-card.png byte-identical (site mirror rule).
"""
import io
import os
import tempfile
import urllib.request

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

# ── card content ────────────────────────────────────────────────────────────
CARD = {
    "wordmark": "unpingable",
    "essence": "Evidence · authority · action",
    "author": "James Beck",
    "domain": "unpingable.com",
}

# ── palette (site light theme; see :root in the pages) ──────────────────────
BG = (245, 244, 239)      # --bg      #f5f4ef
FG = (26, 26, 26)         # --fg      #1a1a1a
MUTED = (85, 83, 80)      # --fg-muted #555350
FAINT = (138, 134, 128)   # --fg-faint #8a8680
ACCENT = (160, 66, 42)    # --accent  #a0422a

W, H = 1200, 630
PAD = 100

GEIST_BASE = "https://cdn.jsdelivr.net/npm/geist@1.3.1/dist/fonts/geist-mono/"


def fetch_ttf(woff2_name, out_path):
    """Fetch a Geist Mono woff2 and rewrite it as a plain ttf Pillow can load."""
    data = urllib.request.urlopen(GEIST_BASE + woff2_name, timeout=30).read()
    font = TTFont(io.BytesIO(data))
    font.flavor = None  # drop woff2 compression -> plain ttf
    font.save(out_path)
    return out_path


def render(out_path):
    with tempfile.TemporaryDirectory() as tmp:
        semibold = fetch_ttf("GeistMono-SemiBold.woff2", os.path.join(tmp, "sb.ttf"))
        regular = fetch_ttf("GeistMono-Regular.woff2", os.path.join(tmp, "rg.ttf"))

        f_word = ImageFont.truetype(semibold, 112)
        f_ess = ImageFont.truetype(regular, 42)
        f_auth = ImageFont.truetype(regular, 26)
        f_dom = ImageFont.truetype(regular, 24)

        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        d.rectangle([0, 0, 10, H], fill=ACCENT)                      # left accent bar
        d.text((PAD, 196), CARD["wordmark"], font=f_word, fill=FG)   # wordmark
        d.rectangle([PAD, 345, PAD + 132, 348], fill=ACCENT)         # accent rule
        d.text((PAD, 378), CARD["essence"], font=f_ess, fill=MUTED)  # essence line
        d.text((PAD, 512), CARD["author"], font=f_auth, fill=FAINT)  # author (bl)

        dw = d.textlength(CARD["domain"], font=f_dom)                # domain (br)
        d.text((W - PAD - dw, 514), CARD["domain"], font=f_dom, fill=FAINT)

        img.save(out_path)
    return out_path


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "og-card.png")
    out = os.path.normpath(out)
    render(out)
    print("wrote", out)
