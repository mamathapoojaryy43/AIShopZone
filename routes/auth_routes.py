"""Authentication: login, signup, logout, password recovery, and wishlist."""
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, Product, Cart, Wishlist, UserActivity, Order

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _safe_next(next_page, default_endpoint="product.index"):
    """Only allow internal redirects (prevents open-redirect attacks)."""
    if next_page and next_page.startswith("/") and not next_page.startswith("//"):
        return redirect(next_page)
    return redirect(url_for(default_endpoint))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("product.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.name}!", "success")
            return _safe_next(request.args.get("next"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("product.index"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm") or ""

        if not name or not email or not password:
            flash("All fields are required.", "warning")
        elif password != confirm:
            flash("Passwords do not match.", "warning")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "warning")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created — welcome to AIShopzone!", "success")
            return _safe_next(request.args.get("next"))

    return render_template("signup.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("product.index"))


@auth_bp.route("/profile")
@login_required
def profile():
    """Account overview: details, recent orders and wishlist count."""
    order_count = current_user.orders.count()
    wishlist_count = current_user.wishlist_items.count()
    recent_orders = (
        current_user.orders.order_by(Order.created_at.desc()).limit(5).all()
    )
    return render_template(
        "profile.html",
        order_count=order_count,
        wishlist_count=wishlist_count,
        recent_orders=recent_orders,
    )


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        # No email backend yet — acknowledge without revealing account existence.
        flash("If that email exists, a reset link is on its way.", "info")
        return redirect(url_for("auth.login"))
    return render_template("forgot.html")


# ---------------- Wishlist ----------------
def _wishlist_count():
    return Wishlist.query.filter_by(user_id=current_user.id).count()


@auth_bp.route("/wishlist")
@login_required
def wishlist():
    """Grid of products the user has saved."""
    items = current_user.wishlist_items.all()
    products = [it.product for it in items]
    return render_template("wishlist.html", products=products)


@auth_bp.route("/wishlist/toggle", methods=["POST"])
@login_required
def wishlist_toggle():
    """Add/remove a product from the wishlist (idempotent toggle).

    Returns JSON for AJAX calls (product-card heart) or redirects back to the
    wishlist page for plain form posts (the Remove button).
    """
    data = request.get_json(silent=True) or request.form
    try:
        product_id = int(data.get("product_id"))
    except (TypeError, ValueError):
        if request.is_json:
            return jsonify({"ok": False, "error": "invalid"}), 400
        return redirect(url_for("auth.wishlist"))

    if not Product.query.get(product_id):
        if request.is_json:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return redirect(url_for("auth.wishlist"))

    item = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        in_wishlist = False
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product_id))
        # Track the wishlist action to power recommendations.
        db.session.add(UserActivity(
            user_id=current_user.id, product_id=product_id, action_type="wishlist"
        ))
        in_wishlist = True
    db.session.commit()

    if request.is_json:
        return jsonify({"ok": True, "in_wishlist": in_wishlist, "count": _wishlist_count()})
    return redirect(url_for("auth.wishlist"))


@auth_bp.route("/wishlist/move", methods=["POST"])
@login_required
def wishlist_move():
    """Move a wishlisted product into the cart, then drop it from the wishlist."""
    try:
        product_id = int(request.form.get("product_id"))
    except (TypeError, ValueError):
        return redirect(url_for("auth.wishlist"))

    product = Product.query.get(product_id)
    if product:
        item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            item.quantity += 1
        else:
            db.session.add(Cart(user_id=current_user.id, product_id=product_id, quantity=1))
        Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).delete()
        db.session.commit()
        flash(f"Moved “{product.name}” to your cart.", "success")
    return redirect(url_for("cart.cart"))
