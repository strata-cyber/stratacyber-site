"""Pull brand assets out of the Strata Cyber brand kit into static/.

Run once (or whenever the kit changes). The output is committed, so the
site build itself never needs the kit, fonttools or Pillow.

    .venv/Scripts/python tools/brand_assets.py [path/to/Strata Cyber Brand Kit]
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from fontTools import subset
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
DEFAULT_KIT = Path.home() / "Área de Trabalho/Strata/Marketing/Strata Cyber Brand Kit"

INK = (21, 23, 26)
GARNET = (158, 31, 50)
GARNET_TINT = (242, 218, 223)
PAPER = (246, 244, 239)
STONE = (167, 169, 166)
GHOST = (34, 37, 41)

# Latin, Latin-1, Latin Ext-A, punctuation, euro, arrows, black square, minus.
UNICODES = "U+0000-00FF,U+0100-017F,U+2000-206F,U+20AC,U+2122,U+2190-2193,U+25A0,U+2212"

FONTS = {
    # output name: source file
    "archivo-400": "Archivo-Regular.ttf",
    "archivo-400i": "Archivo-Italic.ttf",
    "archivo-600": "Archivo-SemiBold.ttf",
    "archivo-600i": "Archivo-SemiBoldItalic.ttf",
    "archivo-expanded-700": "ArchivoExpanded-Bold.ttf",
    "archivo-expanded-800": "ArchivoExpanded-ExtraBold.ttf",
    "jetbrains-mono-400": "JetBrainsMono-Regular.ttf",
    "jetbrains-mono-700": "JetBrainsMono-Bold.ttf",
}


def fonts(kit: Path) -> None:
    out = STATIC / "fonts"
    out.mkdir(parents=True, exist_ok=True)
    for name, src in FONTS.items():
        args = [
            str(kit / "03 Fontes - Fonts" / src),
            f"--unicodes={UNICODES}",
            "--layout-features=kern,liga,calt,ccmp,locl,mark,mkmk,tnum,case",
            "--flavor=woff2",
            f"--output-file={out / (name + '.woff2')}",
        ]
        subset.main(args)
        print("font", name, (out / f"{name}.woff2").stat().st_size // 1024, "KB")
    for lic in ("OFL - Archivo.txt", "OFL - JetBrains Mono.txt"):
        shutil.copy(kit / "03 Fontes - Fonts" / lic, out / lic.replace(" ", ""))


def recolor(svg: str, color: str = "currentColor") -> str:
    return re.sub(r'fill="#[0-9A-Fa-f]{6}"', f'fill="{color}"', svg)


def logos(kit: Path) -> None:
    out = STATIC / "brand"
    out.mkdir(parents=True, exist_ok=True)
    logo = kit / "01 Logo"
    # Logos are drawn with currentColor so CSS picks the brand-approved colour
    # for each background (Charcoal on light, Paper/White on Ink).
    for lockup, folder in (("horizontal", "Horizontal"), ("icon", "Simbolo - Icon"),
                           ("stacked", "Vertical - Stacked"), ("wordmark", "Logotipo - Wordmark")):
        svg = (logo / folder / "SVG" / f"strata-cyber_{lockup}_charcoal.svg").read_text("utf-8")
        svg = re.sub(r'\s(width|height)="\d+"', "", svg, count=2)
        (out / f"{lockup}.svg").write_text(recolor(svg), "utf-8")
    # One external sprite so every page reuses the cached logo and knight via <use>.
    symbols = []
    for lockup in ("horizontal", "icon"):
        svg = (out / f"{lockup}.svg").read_text("utf-8")
        vb = re.search(r'viewBox="([^"]+)"', svg).group(1)
        inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg.strip())
        symbols.append(f'<symbol id="{lockup}" viewBox="{vb}">{inner}</symbol>')
    (out / "sprite.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">' + "".join(symbols) + "</svg>", "utf-8")
    fav = logo / "Favicon"
    for f in ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        shutil.copy(fav / f, STATIC / f)


def og_image(kit: Path, lang: str, eyebrow: str, title: list[str]) -> None:
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    # Ghost knight, cropped off the right edge, a shade off the background.
    knight = Image.open(kit / "01 Logo/Simbolo - Icon/PNG/strata-cyber_icon_white_2400px.png").convert("RGBA")
    kh = 820
    knight = knight.resize((round(knight.width * kh / knight.height), kh), Image.LANCZOS)
    ghost = Image.new("RGBA", knight.size, GHOST + (255,))
    ghost.putalpha(knight.getchannel("A"))
    img.paste(ghost, (W - int(knight.width * 0.62), -40), ghost)

    d.rectangle((0, 0, 13, H), fill=GARNET)  # garnet spine

    fdir = kit / "03 Fontes - Fonts"
    mono = ImageFont.truetype(str(fdir / "JetBrainsMono-Bold.ttf"), 22)
    disp = ImageFont.truetype(str(fdir / "ArchivoExpanded-ExtraBold.ttf"), 66)
    small = ImageFont.truetype(str(fdir / "JetBrainsMono-Regular.ttf"), 22)

    x = 84
    d.rectangle((x, 96, x + 14, 110), fill=GARNET)
    d.text((x + 30, 103), "  ".join(eyebrow), font=mono, fill=GARNET_TINT, anchor="lm")
    y = 170
    for line in title:
        d.text((x, y), line, font=disp, fill=PAPER)
        y += 82

    logo = Image.open(kit / "01 Logo/Horizontal/PNG/strata-cyber_horizontal_white_600px.png").convert("RGBA")
    lw = 270
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(logo, (x, H - 84 - logo.height), logo)
    d.text((W - 72, H - 84 - logo.height // 2), "stratacyber.com.br", font=small, fill=STONE, anchor="rm")

    img.save(STATIC / f"og-{lang}.png", optimize=True)
    print("og", lang)


def main() -> None:
    kit = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KIT
    if not kit.is_dir():
        sys.exit(f"Brand kit not found: {kit}")
    fonts(kit)
    logos(kit)
    og_image(kit, "pt", ["CONSULTORIA EM RISCO CIBERNÉTICO"],
             ["Risco cibernético,", "medido e reduzido."])
    og_image(kit, "en", ["CYBER RISK CONSULTANCY"],
             ["Cyber risk,", "measured", "and reduced."])


if __name__ == "__main__":
    main()
