"""Admin panel: dashboard, product management (CRUD), and order overview.

Access is gated by `admin_required` — only the configured admin email may
enter. All mutations use POST (create/edit/delete) so they can't be triggered
by a stray GET or a CSRF link.
"""
import functools

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, abort, current_app,
)
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import Product, Order, User, OrderItem

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Categories offered in the product form (requested taxonomy + legacy ones).
ADMIN_CATEGORIES = [
    "Electronics", "Fashion", "Beauty", "Sports", "Furniture", "Kitchen",
    "Books", "Gaming", "Shoes", "Accessories",
    "Home & Kitchen", "Toys & Games", "Sports & Outdoors", "Grocery",
]


def admin_required(view):
    @functools.wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.email != current_app.config.get("ADMIN_EMAIL"):
            return f"Forbidden. Your email: {current_user.email}, Admin email config: {current_app.config.get('ADMIN_EMAIL')}", 403
        return view(*args, **kwargs)
    return wrapped


def _product_from_form(product=None):
    """Validate form data and persist a product (new or edited). Returns the
    product on success, or a list of error strings on failure."""
    name = (request.form.get("name") or "").strip()
    category = (request.form.get("category") or "").strip()
    description = (request.form.get("description") or "").strip()
    image_url = (request.form.get("image_url") or "").strip() or None

    errors = []
    if not name:
        errors.append("Product name is required.")
    if not category:
        errors.append("Category is required.")

    try:
        price = float(request.form.get("price") or 0)
        if price < 0:
            errors.append("Price cannot be negative.")
    except ValueError:
        errors.append("Price must be a number.")
        price = 0.0

    try:
        rating = float(request.form.get("rating") or 0)
        rating = max(0.0, min(5.0, rating))
    except ValueError:
        errors.append("Rating must be a number between 0 and 5.")
        rating = 0.0

    try:
        stock = int(request.form.get("stock") or 0)
        if stock < 0:
            errors.append("Stock cannot be negative.")
    except ValueError:
        errors.append("Stock must be a whole number.")
        stock = 0

    if errors:
        return errors

    if product is None:
        product = Product()
        db.session.add(product)
    product.name = name
    product.category = category
    product.price = round(price, 2)
    product.rating = rating
    product.stock = stock
    product.description = description or None
    product.image_url = image_url
    db.session.commit()
    return product


@admin_bp.route("/")
@admin_required
def dashboard():
    product_count = Product.query.count()
    order_count = Order.query.count()
    user_count = User.query.count()
    revenue = (
        db.session.query(func.coalesce(func.sum(Order.total), 0.0))
        .filter(Order.status == "paid")
        .scalar()
        or 0.0
    )
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    low_stock = Product.query.filter(Product.stock <= 5).order_by(Product.stock).limit(5).all()
    return render_template(
        "admin.html",
        product_count=product_count,
        order_count=order_count,
        user_count=user_count,
        revenue=revenue,
        recent_orders=recent_orders,
        low_stock=low_stock,
    )


@admin_bp.route("/products")
@admin_required
def products():
    q = (request.args.get("q") or "").strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    products = query.order_by(Product.id.desc()).all()
    return render_template("admin_products.html", products=products, q=q,
                           categories=ADMIN_CATEGORIES)


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    if request.method == "POST":
        result = _product_from_form()
        if isinstance(result, Product):
            flash("Product created.", "success")
            return redirect(url_for("admin.products"))
        for e in result:
            flash(e, "danger")
    return render_template("admin_product_form.html", product=None,
                           categories=ADMIN_CATEGORIES)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == "POST":
        result = _product_from_form(product)
        if isinstance(result, Product):
            flash("Product updated.", "success")
            return redirect(url_for("admin.products"))
        for e in result:
            flash(e, "danger")
    return render_template("admin_product_form.html", product=product,
                           categories=ADMIN_CATEGORIES)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f"Deleted “{product.name}”.", "info")
    return redirect(url_for("admin.products"))


@admin_bp.route("/orders")
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    # One aggregate query for item counts instead of o.items.count() per order.
    if orders:
        from models import OrderItem

        counts = dict(
            db.session.query(OrderItem.order_id, func.count(OrderItem.id))
            .filter(OrderItem.order_id.in_([o.id for o in orders]))
            .group_by(OrderItem.order_id)
            .all()
        )
        for o in orders:
            o._item_count = counts.get(o.id, 0)
    return render_template("admin_orders.html", orders=orders)


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    items = order.items.all()
    return render_template("admin_order_detail.html", order=order, items=items)
