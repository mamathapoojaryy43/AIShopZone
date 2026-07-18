"""Product routes, including the homepage and product detail."""
import math
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode

from flask import Blueprint, render_template, jsonify, request, url_for, session
from flask_login import current_user, login_required
from extensions import db
from models import Product, UserActivity
from utils import product_gallery
from recommender import recommend_for_user, popular_products

product_bp = Blueprint("product", __name__)


@product_bp.route("/")
def index():
    """Landing page with hero, categories, new arrivals and best sellers."""
    # Newest products first (highest id = most recently seeded).
    new_arrivals = Product.query.order_by(Product.id.desc()).limit(8).all()
    # Highest rated products for the premium "best sellers" row.
    best_sellers = Product.query.order_by(Product.rating.desc()).limit(4).all()

    # Distinct categories with a product count, for the shop-by-category row.
    categories = (
        db.session.query(Product.category, db.func.count(Product.id))
        .group_by(Product.category)
        .all()
    )
    categories = [{"name": c, "count": n} for c, n in categories]

    # A few featured products to float around the hero image.
    floating = Product.query.order_by(Product.rating.desc()).limit(3).all()

    # Recommendation widgets for the homepage. Keep the two rows disjoint so
    # the page doesn't show the same products twice: "Customers Also Bought"
    # is the top-rated set, while the guest "Recommended For You" row pulls the
    # next slice by rating (signed-in users get their personalised mix).
    also_bought = popular_products(limit=8)
    recommended = []
    if current_user.is_authenticated:
        recommended, _ = recommend_for_user(current_user.id, limit=8, try_llm=True)
    if not recommended:
        recommended = popular_products(limit=8, offset=8)

    return render_template(
        "index.html",
        new_arrivals=new_arrivals,
        best_sellers=best_sellers,
        categories=categories,
        floating=floating,
        recommended=recommended,
        also_bought=also_bought,
    )


@product_bp.route("/api/quick-products")
def quick_products():
    """Lightweight JSON list used by client-side widgets (e.g. search)."""
    products = Product.query.order_by(Product.id.desc()).limit(12).all()
    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category,
            }
            for p in products
        ]
    )


@product_bp.route("/recommendations")
@login_required
def recommendations():
    """Dedicated AI-recommendations page for the signed-in shopper."""
    products, source = recommend_for_user(current_user.id, limit=12, try_llm=True)
    return render_template("recommendations.html", products=products, source=source)


@product_bp.route("/products")
def products():
    """Browse, filter, sort and paginate the product catalog."""
    # ----- Read filters from the query string -----
    q = (request.args.get("q", "", type=str) or "").strip()
    selected_categories = request.args.getlist("category")
    selected_rating = request.args.get("rating", type=int)
    in_stock = request.args.get("in_stock", type=int) == 1
    current_sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    # Price bounds (whole catalog) used to size the slider.
    price_floor_db, price_ceil_db = db.session.query(
        db.func.min(Product.price), db.func.max(Product.price)
    ).one()
    price_floor = int(math.floor(price_floor_db or 0))
    price_ceil = int(math.ceil((price_ceil_db or 0) / 50)) * 50 or 50

    selected_min = request.args.get("min_price", type=float)
    selected_max = request.args.get("max_price", type=float)
    selected_min = price_floor if selected_min is None else selected_min
    selected_max = price_ceil if selected_max is None else selected_max

    # ----- Build the filtered/sorted query -----
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    if selected_categories:
        query = query.filter(Product.category.in_(selected_categories))
    query = query.filter(Product.price >= selected_min, Product.price <= selected_max)
    if selected_rating:
        query = query.filter(Product.rating >= selected_rating)
    if in_stock:
        query = query.filter(Product.stock > 0)

    sort_map = {
        "price_asc": Product.price.asc(),
        "price_desc": Product.price.desc(),
        "rating_desc": Product.rating.desc(),
        "newest": Product.id.desc(),
    }
    query = query.order_by(sort_map.get(current_sort, Product.id.desc()))

    per_page = 9
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # ----- Category list for the sidebar (full catalog) -----
    cat_rows = (
        db.session.query(Product.category, db.func.count(Product.id))
        .group_by(Product.category)
        .all()
    )
    categories = [
        {"name": name, "count": count, "checked": name in selected_categories}
        for name, count in cat_rows
    ]

    # ----- Pagination links that preserve every active filter -----
    def build_page_url(p):
        params = request.args.to_dict(flat=False)
        params["page"] = [str(p)]
        return url_for("product.products") + "?" + urlencode(params, doseq=True)

    pages = []
    for p in pagination.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2):
        if p is None:
            pages.append({"num": None})
        else:
            pages.append(
                {"num": p, "url": build_page_url(p), "active": p == pagination.page}
            )

    prev_url = build_page_url(pagination.prev_num) if pagination.has_prev else None
    next_url = build_page_url(pagination.next_num) if pagination.has_next else None

    # AJAX fragment (used for skeleton loading) when explicitly requested.
    is_partial = request.headers.get("X-Requested-With") == "fetch-partial" or request.args.get("partial") == "1"
    template = "products_grid.html" if is_partial else "products.html"
    return render_template(
        template,
        products=pagination.items,
        categories=categories,
        total=pagination.total,
        q=q,
        selected_categories=selected_categories,
        selected_rating=selected_rating,
        in_stock=in_stock,
        current_sort=current_sort,
        price_floor=price_floor,
        price_ceil=price_ceil,
        selected_min=selected_min,
        selected_max=selected_max,
        pages=pages,
        prev_url=prev_url,
        next_url=next_url,
    )


# ---------- Sample review data (deterministic per product) ----------
_REVIEW_AUTHORS = ["Alex M.", "Jordan P.", "Sam R.", "Taylor K.",
                   "Casey L.", "Morgan D.", "Riley B.", "Jamie S."]
_REVIEW_TITLES = {5: "Absolutely love it!", 4: "Great quality", 3: "Good but...", 2: "Not as expected", 1: "Disappointed"}
_REVIEW_TEXTS = {
    5: ["Exactly what I hoped for. Would buy again!", "Top-notch quality and fast shipping.", "Exceeded my expectations!"],
    4: ["Very happy with this purchase.", "Good product, minor nitpicks.", "Solid and reliable."],
    3: ["Does the job, nothing fancy.", "Okay for the price.", "Mixed feelings overall."],
    2: ["Had some issues but support helped.", "Not bad, not great."],
    1: ["Didn't work out for me.", "Wouldn't repurchase."],
}


def build_sample_reviews(product):
    rnd = random.Random(product.id)
    n = rnd.randint(4, 7)
    pool = [5, 5, 5, 4, 4, 4, 3, 3, 2, 1]
    reviews = []
    base = datetime.utcnow()
    for _ in range(n):
        r = rnd.choice(pool)
        days = rnd.randint(1, 120)
        reviews.append({
            "author": rnd.choice(_REVIEW_AUTHORS),
            "rating": r,
            "title": _REVIEW_TITLES[r],
            "comment": rnd.choice(_REVIEW_TEXTS[r]),
            "date": (base - timedelta(days=days)).strftime("%b %d, %Y"),
        })
    reviews.sort(key=lambda x: x["rating"], reverse=True)
    avg = round(sum(r["rating"] for r in reviews) / n, 1)
    dist = {s: sum(1 for r in reviews if r["rating"] == s) for s in range(5, 0, -1)}
    return reviews, {"count": n, "avg": avg, "dist": dist}


@product_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    """Premium product detail page."""
    product = Product.query.get_or_404(product_id)

    # Log a "view" for signed-in users (feeds AI recommendations).
    if current_user.is_authenticated:
        db.session.add(UserActivity(
            user_id=current_user.id, product_id=product.id, action_type="view"
        ))
        db.session.commit()

    # Recently viewed (session-based, works for guests too).
    recent = session.get("recently_viewed", [])
    recent = [i for i in recent if i != product.id]
    recent.insert(0, product.id)
    session["recently_viewed"] = recent[:8]

    gallery = product_gallery(product)

    related = (
        Product.query.filter(Product.category == product.category, Product.id != product.id)
        .order_by(Product.rating.desc())
        .limit(4)
        .all()
    )

    recent_ids = [i for i in session.get("recently_viewed", []) if i != product.id][:4]
    recently_viewed = (
        sorted(
            Product.query.filter(Product.id.in_(recent_ids)).all(),
            key=lambda p: recent_ids.index(p.id),
        )
        if recent_ids
        else []
    )

    if current_user.is_authenticated:
        recommendations, _ = recommend_for_user(current_user.id, limit=4, try_llm=True)
    else:
        recommendations = popular_products(limit=4)
    reviews, rating_summary = build_sample_reviews(product)

    return render_template(
        "product_detail.html",
        product=product,
        gallery=gallery,
        related=related,
        recently_viewed=recently_viewed,
        recommendations=recommendations,
        reviews=reviews,
        rating_summary=rating_summary,
    )
