"""Genera el icono de AskForever (bocadillo dorado con interrogación sobre fondo marrón oscuro).

Uso:  python scripts/make-icons.py
Salida:
  addon/AskForever/Media/Icon.tga          64x64, retrato de las ventanas (fondo a sangre)
  addon/AskForever/Media/MinimapIcon.tga   64x64, disco con esquinas transparentes
  docs/img/logo.png                        400x400, logo para la página de CurseForge
TGA sin comprimir y con alfa de 8 bits, como los de Lorewake.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SCALE = 16  # dibujamos a gran tamaño y reducimos para suavizar los bordes
SIZE = 64 * SCALE

BG = (21, 16, 11, 255)        # #15100b
BG_EDGE = (46, 36, 24, 255)   # #2e2418
GOLD = (230, 184, 74, 255)    # #e6b84a
GOLD_DEEP = (184, 145, 74, 255)  # #b8914a
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\georgiab.ttf",
    r"C:\Windows\Fonts\timesbd.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]


def load_font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("No se encontró ninguna fuente para dibujar la interrogación.")


def draw_art(full_bleed):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = SIZE / 2

    if full_bleed:
        d.rectangle([0, 0, SIZE, SIZE], fill=BG)
    else:
        d.ellipse([0, 0, SIZE - 1, SIZE - 1], fill=BG)
        d.ellipse([SIZE * 0.02, SIZE * 0.02, SIZE * 0.98, SIZE * 0.98], outline=GOLD_DEEP, width=int(SIZE * 0.035))

    # Bocadillo: rectángulo redondeado con cola abajo a la izquierda.
    left, top, right, bottom = SIZE * 0.20, SIZE * 0.22, SIZE * 0.80, SIZE * 0.66
    d.rounded_rectangle([left, top, right, bottom], radius=SIZE * 0.14, fill=GOLD)
    d.polygon([(SIZE * 0.30, bottom - SIZE * 0.02), (SIZE * 0.28, SIZE * 0.82), (SIZE * 0.50, bottom - SIZE * 0.02)], fill=GOLD)

    # Interrogación centrada en el bocadillo.
    font = load_font(int(SIZE * 0.42))
    d.text((c, (top + bottom) / 2 + SIZE * 0.01), "?", font=font, fill=BG, anchor="mm")
    return img


def save_tga(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, compression=None)
    print("Creado:", path.relative_to(ROOT))


def main():
    portrait = draw_art(full_bleed=True).resize((64, 64), Image.LANCZOS)
    minimap = draw_art(full_bleed=False).resize((64, 64), Image.LANCZOS)
    save_tga(portrait, ROOT / "addon/AskForever/Media/Icon.tga")
    save_tga(minimap, ROOT / "addon/AskForever/Media/MinimapIcon.tga")

    logo = draw_art(full_bleed=False).resize((400, 400), Image.LANCZOS)
    flat = Image.new("RGBA", (400, 400), BG)
    flat.alpha_composite(logo)
    out = ROOT / "docs/img/logo.png"
    flat.convert("RGB").save(out)
    print("Creado:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
