"""Shopping cart: add / view / update / remove / coupon."""
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, jsonify, session,
)
from flask_login import login_required, current_user

from extensions import db
from models import Product, Cart

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")
cart_bp.strict_slashes = False

SHIPPING_FLAT = 49.0
FREE_SHIPPING_THRESHOLD = 499.0
TAX_RATE = 0.18  # India GST
COUPONS = {"SAVE10": 0.10, "WELCOME5": 0.05}


def cart_count():
    from sqlalchemy import func

    return (
        db.session.query(func.coalesce(func.sum(Cart.quantity), 0))
        .filter_by(user_id=current_user.id)
        .scalar()
        or 0
    )


def compute_totals(subtotal, discount):
    taxable = max(subtotal - discount, 0.0)
    shipping = 0.0 if subtotal <= 0 else (
        0.0 if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FLAT
    )
    tax = taxable * TAX_RATE
    grand = taxable + shipping + tax
    return shipping, tax, grand


@cart_bp.route("/add", methods=["POST"])
@login_required
def add():
    data = request.get_json(silent=True) or request.form
    try:
        product_id = int(data.get("product_id"))
        qty = max(1, int(data.get("quantity", 1)))
    except (TypeError, ValueError):
        if request.is_json:
            return jsonify({"ok": False, "error": "invalid"}), 400
        return redirect(url_for("product.products"))

    product = Product.query.get(product_id)
    if not product:
        if request.is_json:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return redirect(url_for("product.products"))

    item = Cart.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if item:
        item.quantity += qty
    else:
        db.session.add(Cart(user_id=current_user.id, product_id=product.id, quantity=qty))
    db.session.commit()

    if request.is_json:
        return jsonify({"ok": True, "count": cart_count()})
    return redirect(request.referrer or url_for("cart.cart"))


@cart_bp.route("/", methods=["GET"])
@login_required
def cart():
    from sqlalchemy.orm import joinedload

    # joinedload the product to avoid one query per cart line (N+1).
    items = current_user.cart_items.options(joinedload(Cart.product)).all()
    subtotal = 0.0
    rows = []
    for item in items:
        product = item.product
        line_total = item.quantity * product.price
        subtotal += line_total
        rows.append({"cart": item, "product": product, "line_total": line_total})

    coupon = session.get("coupon")
    discount = round(subtotal * COUPONS[coupon], 2) if coupon in COUPONS else 0.0
    shipping, tax, grand = compute_totals(subtotal, discount)

    return render_template(
        "cart.html",
        items=rows,
        subtotal=subtotal,
        discount=discount,
        coupon=coupon,
        shipping=shipping,
        tax=tax,
        tax_rate=TAX_RATE,
        grand=grand,
    )


@cart_bp.route("/update", methods=["POST"])
@login_required
def update():
    try:
        product_id = int(request.form.get("product_id"))
        qty = max(1, int(request.form.get("quantity", 1)))
    except (TypeError, ValueError):
        return redirect(url_for("cart.cart"))
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        item.quantity = qty
        db.session.commit()
    return redirect(url_for("cart.cart"))


@cart_bp.route("/remove", methods=["POST"])
@login_required
def remove():
    try:
        product_id = int(request.form.get("product_id"))
    except (TypeError, ValueError):
        return redirect(url_for("cart.cart"))
    Cart.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
    db.session.commit()
    return redirect(url_for("cart.cart"))


@cart_bp.route("/coupon", methods=["POST"])
@login_required
def coupon():
    code = (request.form.get("code") or "").strip().upper()
    if code in COUPONS:
        session["coupon"] = code
        flash(f"Coupon {code} applied!", "success")
    else:
        session.pop("coupon", None)
        flash("Invalid coupon code.", "warning")
    return redirect(url_for("cart.cart"))
