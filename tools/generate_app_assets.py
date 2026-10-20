"""
Generate app icon and splash screen using CTUT logo (ctut.webp).
"""
from PIL import Image, ImageDraw, ImageFont
import os

BG_DARK = (15, 23, 42)
ACCENT  = (56, 189, 248)
WHITE   = (255, 255, 255)


def make_icon(logo_path, size=1024):
    """Create app icon with CTUT logo on dark rounded background."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = int(size * 0.02)
    radius = int(size * 0.18)
    d.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius, fill=BG_DARK
    )
    for i in range(60):
        alpha = max(0, 40 - i)
        r = int(size * 0.4 - i * size * 0.004)
        if r <= 0: break
        cx, cy = size // 2, size // 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 58, 138, alpha))
    logo = Image.open(logo_path).convert('RGBA')
    logo_size = int(size * 0.70)
    logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
    lx = (size - logo.width) // 2
    ly = (size - logo.height) // 2
    img.paste(logo, (lx, ly), logo)
    return img


def make_splash(logo_path, width=1080, height=1920):
    """Create splash screen with CTUT logo centered on dark background."""
    img_rgba = Image.new('RGBA', (width, height), (*BG_DARK, 255))
    d = ImageDraw.Draw(img_rgba)
    for i in range(80):
        alpha = max(0, 25 - int(i * 0.3))
        r = int(min(width, height) * 0.35 - i * 3)
        if r <= 0: break
        cx, cy = width // 2, int(height * 0.40)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 58, 138, alpha))
    logo = Image.open(logo_path).convert('RGBA')
    logo_size = int(min(width, height) * 0.35)
    logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
    lx = (width - logo.width) // 2
    ly = int(height * 0.32)
    img_rgba.paste(logo, (lx, ly), logo)
    text_y = ly + logo.height + int(logo_size * 0.2)
    font_size = int(logo_size * 0.16)
    sub_size = int(font_size * 0.55)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", font_size)
    except:
        font = ImageFont.load_default()
    try:
        sub_font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", sub_size)
    except:
        sub_font = ImageFont.load_default()
    d2 = ImageDraw.Draw(img_rgba)
    text = "Solar Clean"
    bbox = d2.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    d2.text(((width - tw) // 2, text_y), text, fill=WHITE, font=font)
    sub = "Hệ thống giám sát pin mặt trời"
    bbox2 = d2.textbbox((0, 0), sub, font=sub_font)
    sw = bbox2[2] - bbox2[0]
    sy = text_y + font_size + int(sub_size * 0.5)
    d2.text(((width - sw) // 2, sy), sub, fill=(*ACCENT, 200), font=sub_font)
    return img_rgba.convert('RGB')


def main():
    logo_path = r"D:\DuAn\ctut.webp"
    base_dir = r"D:\DuAn\solar_clean_app"
    res_dir = os.path.join(base_dir, "android", "app", "src", "main", "res")
    assets_dir = os.path.join(base_dir, "assets")
    mipmap_sizes = {
        "mipmap-mdpi": 48, "mipmap-hdpi": 72, "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144, "mipmap-xxxhdpi": 192,
    }
    master = make_icon(logo_path, 1024)
    master.save(os.path.join(assets_dir, "icon.png"))
    print("  Saved: assets/icon.png (1024x1024)")
    for folder, sz in mipmap_sizes.items():
        out_dir = os.path.join(res_dir, folder)
        os.makedirs(out_dir, exist_ok=True)
        resized = master.resize((sz, sz), Image.LANCZOS)
        resized.save(os.path.join(out_dir, "ic_launcher.png"), "PNG")
        print(f"  Saved: {folder}/ic_launcher.png ({sz}x{sz})")
    splash = make_splash(logo_path, 1080, 1920)
    splash.save(os.path.join(assets_dir, "splash.png"), "PNG", quality=95)
    print("  Saved: assets/splash.png (1080x1920)")
    splash_small = make_splash(logo_path, 480, 800)
    drawable_dir = os.path.join(res_dir, "drawable")
    os.makedirs(drawable_dir, exist_ok=True)
    splash_small.save(os.path.join(drawable_dir, "launch_image.png"), "PNG")
    print("  Saved: drawable/launch_image.png (480x800)")
    print("\n Done! All assets generated with CTUT logo!")

if __name__ == "__main__":
    main()
