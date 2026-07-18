"""Generate a unique, name-matched SVG image for every seeded product.

Each product gets its own file at:
    static/images/products/<category-slug>/<n>.svg
where <n> is the 1-based index of the product in seed_data.PRODUCTS.

The image is a premium-looking product card: a category-themed gradient
background, a representative emoji, the product name and price. Because every
product maps to a different file (by index), no two products ever share an
image. Run this before seeding so the referenced files exist on disk.
"""
import os
import xml.sax.saxutils as su

from app import app
from utils import category_slug
from seed_data import PRODUCTS

# (top color, bottom color) per seed category — rich, premium gradients.
CATEGORY_GRADIENTS = {
    "Electronics": ("#4f46e5", "#7c3aed"),
    "Fashion": ("#db2777", "#f43f5e"),
    "Home & Kitchen": ("#ea580c", "#f59e0b"),
    "Books": ("#1d4ed8", "#4f46e5"),
    "Toys & Games": ("#f97316", "#facc15"),
    "Beauty": ("#be185d", "#a855f7"),
    "Sports & Outdoors": ("#059669", "#10b981"),
    "Grocery": ("#65a30d", "#16a34a"),
}

CATEGORY_DEFAULT_EMOJI = {
    "Electronics": "💡",
    "Fashion": "👕",
    "Home & Kitchen": "🍴",
    "Books": "📚",
    "Toys & Games": "🎮",
    "Beauty": "💅",
    "Sports & Outdoors": "⚽",
    "Grocery": "🛒",
}

# Keyword -> emoji (first match wins; checked in order).
EMOJI_TABLE = [
    ("headphone", "🎧"), ("tv", "📺"), ("smartphone", "📱"),
    ("speaker", "🔊"), ("charger", "🔌"), ("charging", "🔌"),
    ("keyboard", "⌨️"), ("smartwatch", "⌚"), ("watch", "🕰️"),
    ("jacket", "🧥"), ("sneaker", "👟"), ("shoe", "👟"),
    ("bag", "👜"), ("sunglass", "🕶️"), ("t-shirt", "👕"),
    ("shirt", "👕"), ("scarf", "🧣"),
    ("cookware", "🍳"), ("coffee", "☕"), ("fryer", "🍟"),
    ("pillow", "🛏️"), ("lamp", "💡"), ("dinnerware", "🍽️"),
    ("vacuum", "🤖"), ("storage", "🫙"),
    ("clean code", "💻"), ("mystery", "📕"), ("cooking", "🍳"),
    ("history", "📜"), ("journal", "📓"), ("space", "🚀"), ("book", "📚"),
    ("building block", "🧱"), ("race car", "🏎️"), ("board game", "🎲"),
    ("teddy", "🧸"), ("puzzle", "🧩"), ("chess", "♟️"),
    ("serum", "🧴"), ("lipstick", "💄"), ("shampoo", "🧼"),
    ("brush", "🖌️"), ("oil", "🌿"),
    ("yoga", "🧘"), ("dumbbell", "🏋️"), ("bottle", "🍶"),
    ("tent", "⛺"), ("foam roller", "🌀"), ("helmet", "🚴"),
    ("tea", "🍵"), ("olive", "🫒"), ("chocolate", "🍫"), ("nuts", "🥜"),
]


def pick_emoji(name, category):
    n = name.lower()
    for key, emo in EMOJI_TABLE:
        if key in n:
            return emo
    return CATEGORY_DEFAULT_EMOJI.get(category, "📦")


def wrap_name(name, max_width=840):
    """Return (lines, font_size) that fit the name in <=3 centered lines."""
    words = name.split()
    size = 52
    while size >= 26:
        max_chars = max(6, int(max_width / (size * 0.58)))
        lines, cur = [], ""
        for w in words:
            cand = w if not cur else cur + " " + w
            if len(cand) <= max_chars:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= 3 and all(len(l) <= max_chars for l in lines):
            return lines, size
        size -= 3
    return [name[:40]], 26


def build_svg(name, price, emoji, grad):
    c1, c2 = grad
    aria = su.escape(name, {'"': "&quot;", "'": "&#39;"})
    lines, size = wrap_name(name)
    line_h = size * 1.18
    total_h = len(lines) * line_h
    center = 775
    start_y = center - total_h / 2 + line_h / 2
    name_text = ""
    for i, line in enumerate(lines):
        y = start_y + i * line_h
        name_text += (
            f'<text x="500" y="{y:.0f}" font-family="Inter, Arial, sans-serif" '
            f'font-size="{size}" font-weight="700" fill="#2b2622" '
            f'text-anchor="middle">{su.escape(line)}</text>\n    '
        )
    price_str = f"₹{price:,.2f}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000" role="img" aria-label="{aria}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.34" r="0.62">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.30"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1000" height="1000" fill="url(#bg)"/>
  <rect width="1000" height="1000" fill="url(#glow)"/>
  <circle cx="110" cy="120" r="130" fill="#ffffff" opacity="0.07"/>
  <circle cx="910" cy="930" r="170" fill="#000000" opacity="0.05"/>
  <text x="48" y="72" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="800" fill="#ffffff" opacity="0.92">AIShopzone</text>
  <text x="500" y="420" font-size="360" text-anchor="middle" dominant-baseline="central">{emoji}</text>
  <rect x="50" y="700" width="900" height="252" rx="30" fill="#ffffff" opacity="0.96"/>
    {name_text}  <text x="500" y="918" font-family="Inter, Arial, sans-serif" font-size="44" font-weight="800" fill="#ff6b4a" text-anchor="middle">{price_str}</text>
</svg>
'''


def main():
    count = 0
    for idx, (name, category, price, _rating, _stock, _desc) in enumerate(PRODUCTS, start=1):
        slug = category_slug(category)
        folder = os.path.join(app.static_folder, "images", "products", slug)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{idx}.svg")
        grad = CATEGORY_GRADIENTS.get(category, ("#6366f1", "#8b5cf6"))
        emoji = pick_emoji(name, category)
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(name, price, emoji, grad))
        assert os.path.isfile(path), f"failed to write {path}"
        count += 1
        print(f"  {idx:2d}. {slug}/{idx}.svg  {name}")
    print(f"\nGenerated {count} product images under static/images/products/.")


if __name__ == "__main__":
    main()
