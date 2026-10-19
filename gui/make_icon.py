import sys

from PIL import Image

SIZES = [16, 24, 32, 40, 48, 64, 96, 128, 256]
MARGIN = 0.02


def main(src, dst):
    img = Image.open(src).convert("RGBA")

    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)

    side = int(max(img.size) * (1 + MARGIN * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)

    master = canvas.resize((512, 512), Image.LANCZOS)
    master.save(dst, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Wrote {dst} with sizes {SIZES}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
