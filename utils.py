"""Shared helpers for image resolution and product galleries.

Automatic image system (priority order):
  1. Product image  -> product.image_url (only if the local file exists)
  2. Category image -> static/images/categories/<slug>.jpg (if it exists)
  3. Placeholder    -> static/images/placeholder.jpg (always exists)

Every helper returns a URL that points at a real file, so a broken image
is never rendered. A capture-phase `error` listener in main.js additionally
swaps any <img> that still fails to load (e.g. a remote URL) to the
placeholder, covering content loaded via the AJAX grid too.
"""
import os

from flask import url_for, current_app

# Category name (slug) -> image filename (no extension) under
# static/images/categories. Any entry whose file is missing simply falls
# back to the placeholder, so this map is safe to extend as new category
# artwork is dropped into static/images/categories.
CATEGORY_IMAGES = {
    # ---- requested categories ----
    "fashion": "fashion",
    "electronics": "electronics",
    "beauty": "beauty",
    "sports": "sports-outdoors",   # reuse existing sports artwork
    "furniture": "furniture",      # no artwork yet -> placeholder
    "kitchen": "home-kitchen",     # reuse existing kitchen artwork
    "books": "books",
    "gaming": "gaming",            # no artwork yet -> placeholder
    "shoes": "shoes",              # no artwork yet -> placeholder
    "accessories": "accessories",  # no artwork yet -> placeholder
    # ---- legacy seeded aliases (keep existing catalog data working) ----
    "sports-outdoors": "sports-outdoors",
    "home-kitchen": "home-kitchen",
    "grocery": "grocery",
    "toys-games": "toys-games",
}

PLACEHOLDER = "images/placeholder.jpg"


def category_slug(category):
    return (
        (category or "")
        .lower()
        .replace(" & ", "-")
        .replace("/", "-")
        .replace(" ", "-")
    )


def _static_exists(rel):
    """True if `rel` exists on disk inside the static folder."""
    if not rel:
        return False
    return os.path.isfile(os.path.join(current_app.static_folder, rel))


def _resolve_local(value):
    """Return a static URL for `value`, but only if the file truly exists.

    Accepts bare filenames, 'images/...' paths and '/static/...' paths.
    Remote (http/https) URLs are returned as-is (the browser verifies them
    and the client-side onerror net catches any failure). Returns None when
    the value is missing, empty, or points at a file that isn't there.
    """
    if not value or not isinstance(value, str):
        return None
    if value.startswith(("http://", "https://", "//")):
        return value
    rel = value
    if rel.startswith("/static/"):
        rel = rel[len("/static/"):]
    elif rel.startswith("static/"):
        rel = rel[len("static/"):]
    rel = rel.lstrip("/")
    if not rel:
        return None
    if _static_exists(rel):
        return url_for("static", filename=rel)
    return None


def product_image_url(product):
    """Product image (if it exists) -> category image -> placeholder."""
    local = _resolve_local(getattr(product, "image_url", None))
    if local:
        return local
    return category_image_url(product.category)


def category_image_url(category):
    """Category image (if it exists) -> placeholder."""
    slug = category_slug(category)
    fname = CATEGORY_IMAGES.get(slug, slug)
    rel = f"images/categories/{fname}.jpg"
    if _static_exists(rel):
        return url_for("static", filename=rel)
    return url_for("static", filename=PLACEHOLDER)


# Extensions we treat as displayable product artwork.
_GALLERY_EXTS = (".jpg", ".jpeg", ".png", ".svg", ".webp")


def product_gallery(product):
    """Ordered gallery: product image(s) -> category image -> placeholder.

    Scans the product's category folder for any artwork (jpg/svg/png/webp) so
    the detail-page gallery shows several thumbnails even when only a single
    "primary" image is stored on the product. A category image is appended as a
    fallback alternate, and the placeholder guarantees the list is never empty.
    """
    imgs = []

    local = _resolve_local(getattr(product, "image_url", None))
    if local:
        imgs.append(local)

    folder = f"images/products/{category_slug(product.category)}"
    base = os.path.join(current_app.static_folder, folder)
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            if entry.lower().endswith(_GALLERY_EXTS):
                rel = f"{folder}/{entry}"
                url = url_for("static", filename=rel)
                if _static_exists(rel) and url not in imgs:
                    imgs.append(url)

    # Guarantee at least a category image alternate (keeps the gallery from
    # collapsing to a single thumbnail), then the placeholder.
    cat_img = category_image_url(product.category)
    if cat_img not in imgs:
        imgs.append(cat_img)
    if not imgs:  # final guarantee: never return an empty gallery
        imgs.append(url_for("static", filename=PLACEHOLDER))
    return imgs
