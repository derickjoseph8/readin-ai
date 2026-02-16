"""Generate ReadIn AI brand icons matching the website's gold R design."""

from PIL import Image, ImageDraw, ImageFont
import os

# Colors matching website: from-gold-400 to-gold-600
GOLD_400 = (251, 191, 36)   # #fbbf24
GOLD_600 = (217, 119, 6)    # #d97706
DARK_BG = (30, 30, 46)      # #1e1e2e (premium-bg)

def create_gradient(size, color1, color2):
    """Create a diagonal gradient from top-left to bottom-right."""
    img = Image.new('RGBA', (size, size))
    for y in range(size):
        for x in range(size):
            # Diagonal gradient factor
            factor = (x + y) / (2 * size)
            r = int(color1[0] + (color2[0] - color1[0]) * factor)
            g = int(color1[1] + (color2[1] - color1[1]) * factor)
            b = int(color1[2] + (color2[2] - color1[2]) * factor)
            img.putpixel((x, y), (r, g, b, 255))
    return img

def round_corners(img, radius):
    """Add rounded corners to an image."""
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), img.size], radius=radius, fill=255)
    img.putalpha(mask)
    return img

def generate_icon(size, output_path):
    """Generate a single icon at specified size."""
    # Create gradient background
    img = create_gradient(size, GOLD_400, GOLD_600)

    # Add rounded corners (about 20% of size)
    corner_radius = int(size * 0.2)
    img = round_corners(img, corner_radius)

    draw = ImageDraw.Draw(img)

    # Try to use a bold font, fall back to default
    font_size = int(size * 0.6)
    try:
        # Try common system fonts
        font_names = [
            "C:/Windows/Fonts/arialbd.ttf",  # Windows Arial Bold
            "C:/Windows/Fonts/segoeui.ttf",  # Windows Segoe UI
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        ]
        font = None
        for font_name in font_names:
            if os.path.exists(font_name):
                font = ImageFont.truetype(font_name, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Draw the "R" letter centered
    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]

    # Draw text in dark color
    draw.text((x, y), text, fill=DARK_BG, font=font)

    img.save(output_path)
    print(f"Created: {output_path}")
    return img

def png_to_ico(png_path, ico_path, sizes=[16, 32, 48, 64, 128, 256]):
    """Convert PNG to ICO with multiple sizes."""
    img = Image.open(png_path).convert('RGBA')
    icons = []
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)
    # Save with all sizes embedded
    icons[-1].save(ico_path, format='ICO', append_images=icons[:-1])
    print(f"Created: {ico_path}")

def main():
    # Output directories
    assets_dir = "assets"
    web_app_dir = "web/app"
    extension_dir = "extension/icons"
    extension_edge_dir = "extension-edge/icons"

    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(web_app_dir, exist_ok=True)
    os.makedirs(extension_dir, exist_ok=True)
    os.makedirs(extension_edge_dir, exist_ok=True)

    print("Generating ReadIn AI icons with gold gradient R design...\n")

    # Desktop app icons
    print("=== Desktop App Icons ===")
    generate_icon(256, f"{assets_dir}/icon.png")
    generate_icon(512, f"{assets_dir}/icon_512.png")
    png_to_ico(f"{assets_dir}/icon_512.png", f"{assets_dir}/icon.ico")

    # Web favicon (Next.js app directory convention)
    print("\n=== Web Favicon ===")
    generate_icon(32, f"{web_app_dir}/favicon.ico")
    generate_icon(180, f"{web_app_dir}/apple-icon.png")
    generate_icon(192, f"{web_app_dir}/icon.png")

    # Browser extension icons
    print("\n=== Browser Extension Icons ===")
    for ext_dir in [extension_dir, extension_edge_dir]:
        generate_icon(16, f"{ext_dir}/icon16.png")
        generate_icon(48, f"{ext_dir}/icon48.png")
        generate_icon(128, f"{ext_dir}/icon128.png")

    print("\n✅ All icons generated successfully!")
    print("\nNext steps:")
    print("1. Rebuild the desktop app: pyinstaller build.spec")
    print("2. Rebuild web: cd web && npm run build")
    print("3. Rebuild extensions if needed")

if __name__ == "__main__":
    main()
