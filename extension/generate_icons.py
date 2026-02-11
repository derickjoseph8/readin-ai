"""
Generate extension icons for ReadIn AI
Run this script once to create the icon files
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, output_path):
    """Create a single icon of the specified size"""
    # Create image with gradient-like green background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded rectangle background
    padding = size // 8
    corner_radius = size // 4

    # Draw green gradient-like background (solid green for simplicity)
    for i in range(size):
        # Gradient from lighter to darker green
        ratio = i / size
        r = int(34 + (22 - 34) * ratio)
        g = int(197 + (163 - 197) * ratio)
        b = int(94 + (74 - 94) * ratio)
        draw.line([(0, i), (size, i)], fill=(r, g, b, 255))

    # Create rounded corners by masking
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (size-1, size-1)], radius=corner_radius, fill=255)
    img.putalpha(mask)

    # Draw the "R" letter
    draw = ImageDraw.Draw(img)

    # Try to use a system font, fall back to default
    font_size = int(size * 0.6)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except:
            font = ImageFont.load_default()

    # Get text bounding box for centering
    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (size - text_width) // 2
    y = (size - text_height) // 2 - bbox[1]

    # Draw white text
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

    # Save
    img.save(output_path, 'PNG')
    print(f"Created {output_path}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(script_dir, 'icons')

    os.makedirs(icons_dir, exist_ok=True)

    sizes = [16, 48, 128]

    for size in sizes:
        output_path = os.path.join(icons_dir, f'icon{size}.png')
        create_icon(size, output_path)

    print("\nAll icons created successfully!")
    print("You can now load the extension in Chrome.")

if __name__ == '__main__':
    main()
