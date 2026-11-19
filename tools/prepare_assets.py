#!/usr/bin/env python3
"""Optimise the supplied school assets into the public assets folder.

Only the supplied files are used; nothing is generated or invented.
Run: python tools/prepare_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
IMAGES = ASSETS / "images"
MAX_WIDTH = 1600
WEBP_QUALITY = 82

SOURCE = {
    "logo": "logo ops 2nd.png",
    "real": "school real picwebp.jfif",
    "slideshow": "pic for slide show.jpg",
    "illustration": "Gemini_Generated_Image_6btwyq6btwyq6btw.jfif",
}

# Additional pictures supplied for the gallery, in display order.
# AI-generated files are labelled as illustrative on the public site.
EXTRA_GALLERY = [
    "Gemini_Generated_Image_6ts6o86ts6o86ts6.jfif",
    "Gemini_Generated_Image_8iwjvw8iwjvw8iwj (2).jfif",
    "Gemini_Generated_Image_8iwjvw8iwjvw8iwj (3).jfif",
    "Gemini_Generated_Image_8iwjvw8iwjvw8iwj (4).jfif",
    "WhatsApp Image 2026-11-19 at 6.11.33 AM.jpeg",
]


def source_path(key: str) -> Path:
    path = ROOT / SOURCE.get(key, key)
    if not path.is_file():
        raise SystemExit(f"Missing supplied asset: {path}")
    return path


def fit_width(image: Image.Image, width: int = MAX_WIDTH) -> Image.Image:
    if image.width <= width:
        return image
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def cover_crop(image: Image.Image, ratio: float) -> Image.Image:
    target_width, target_height = image.width, round(image.width / ratio)
    if target_height > image.height:
        target_height = image.height
        target_width = round(image.height * ratio)
    left = (image.width - target_width) // 2
    top = (image.height - target_height) // 2
    return image.crop((left, top, left + target_width, top + target_height))


def save_webp(image: Image.Image, name: str, quality: int = WEBP_QUALITY) -> None:
    path = IMAGES / name
    image.convert("RGB").save(
        path, "WEBP", quality=quality, method=6, exact=False
    )
    print(f"{name:24} {image.width:>5} x {image.height:<5} {path.stat().st_size / 1024:>8.1f} KB")


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)

    # Logo: trim transparent padding, keep alpha, cap at 512 px.
    logo = Image.open(source_path("logo")).convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    if bbox:
        logo = logo.crop(bbox)
    logo.thumbnail((512, 512), Image.Resampling.LANCZOS)
    logo_path = ASSETS / "logo.png"
    logo.save(logo_path, "PNG", optimize=True)
    print(f"{'logo.png':24} {logo.width:>5} x {logo.height:<5} {logo_path.stat().st_size / 1024:>8.1f} KB")

    # Favicon on a white plate so the dark crest stays visible at tiny sizes.
    size = 128
    favicon = Image.new("RGB", (size, size), "white")
    mark = logo.copy()
    mark.thumbnail((size - 16, size - 16), Image.Resampling.LANCZOS)
    favicon.paste(mark, ((size - mark.width) // 2, (size - mark.height) // 2), mark)
    favicon_path = ASSETS / "favicon.png"
    favicon.save(favicon_path, "PNG", optimize=True)
    print(f"{'favicon.png':24} {size:>5} x {size:<5} {favicon_path.stat().st_size / 1024:>8.1f} KB")

    real = Image.open(source_path("real")).convert("RGB")
    slideshow = Image.open(source_path("slideshow")).convert("RGB")
    illustration = Image.open(source_path("illustration")).convert("RGB")

    # Hero: not lazy-loaded, so keep a sensible file size.
    hero = fit_width(real)
    save_webp(hero, "hero.webp", 80)

    # About section building photograph.
    save_webp(fit_width(cover_crop(real, 4 / 3), 1400), "school-building.webp")

    # Gallery.
    save_webp(fit_width(slideshow), "gallery-1.webp")
    save_webp(fit_width(cover_crop(real, 16 / 9), 1400), "gallery-2.webp")
    save_webp(fit_width(illustration), "gallery-3.webp", 78)

    for number, filename in enumerate(EXTRA_GALLERY, start=4):
        extra = Image.open(source_path(filename)).convert("RGB")
        save_webp(fit_width(extra), f"gallery-{number}.webp", 78)

    print("\nAll outputs written from supplied assets only.")


if __name__ == "__main__":
    main()
