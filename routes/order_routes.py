"""Order routes: checkout, order history, order detail, and success page."""
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash, abort,
)
from flask_login import login_required, current_user

from extensions import db
from models import Product, Cart, Order, OrderItem, UserActivity
from recommender import also_bought
from routes.cart_routes import (
    COUPONS,
    SHIPPING_FLAT,
    FREE_SHIPPING_THRESHOLD,
    TAX_RATE,
    compute_totals,
)

order_bp = Blueprint("order", __name__, url_prefix="/orders")


# ----- Fields the checkout form requires -----
CONTACT_SHIPPING_FIELDS = [
    "full_name", "email", "address_line1", "city", "postal_code", "country",
]
PAYMENT_METHODS = ["Credit / Debit Card", "UPI", "Cash on Delivery"]
# Card fields are mock-only — presence is validated, but they are never stored.
CARD_FIELDS = ["cardholder_name", "card_number", "expiry", "cvc"]
UPI_FIELDS = ["upi_id"]

# Used to populate the State / Union Territory dropdown on the checkout form.
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]


def cart_rows_and_subtotal():
    """Build (rows, subtotal) for the signed-in user's cart."""
    from sqlalchemy.orm import joinedload

    # joinedload the product so we don't issue one query per cart line (N+1).
    items = current_user.cart_items.options(joinedload(Cart.product)).all()
    rows, subtotal = [], 0.0
    for item in items:
        product = item.product
        line_total = item.quantity * product.price
        subtotal += line_total
        rows.append({"cart": item, "product": product, "line_total": line_total})
    return rows, subtotal


def order_price_breakdown(subtotal):
    """Reuse the cart's coupon + pricing rules for a consistent total."""
    from flask import session

    coupon = session.get("coupon")
    discount = round(subtotal * COUPONS[coupon], 2) if coupon in COUPONS else 0.0
    shipping, tax, grand = compute_totals(subtotal, discount)
    return coupon, discount, shipping, tax, grand


@order_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    rows, subtotal = cart_rows_and_subtotal()

    # Nothing to buy — send the shopper back to their cart.
    if not rows:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart.cart"))

    coupon, discount, shipping, tax, grand = order_price_breakdown(subtotal)

    # Pre-fill known details so returning users don't retype everything.
    form = {
        "full_name": current_user.name,
        "email": current_user.email,
        "phone": "",
        "address_line1": "",
        "address_line2": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": "India",
        "payment_method": PAYMENT_METHODS[0],
        "cardholder_name": "",
        "card_number": "",
        "expiry": "",
        "cvc": "",
        "upi_id": "",
    }

    if request.method == "POST":
        for key in form:
            form[key] = (request.form.get(key) or "").strip()

        missing = [f for f in CONTACT_SHIPPING_FIELDS if not form.get(f)]
        if form.get("email") and "@" not in form["email"]:
            missing.append("email")
        # Card details are required only when paying by card (mock validation).
        if form["payment_method"] == "Credit / Debit Card":
            missing += [f for f in CARD_FIELDS if not form.get(f)]
        elif form["payment_method"] == "UPI":
            missing += [f for f in UPI_FIELDS if not form.get(f)]

        if missing:
            flash("Please complete all required fields.", "danger")
            return render_template(
                "checkout.html",
                form=form,
                rows=rows,
                subtotal=subtotal,
                discount=discount,
                shipping=shipping,
                tax=tax,
                grand=grand,
                coupon=coupon,
                tax_rate=TAX_RATE,
                payment_methods=PAYMENT_METHODS,
                indian_states=INDIAN_STATES,
            )

        # Persist the order with a pricing snapshot. Card data is intentionally
        # NOT stored — this is a mock checkout with no real payment processor.
        order = Order(
            user_id=current_user.id,
            status="paid",
            full_name=form["full_name"],
            email=form["email"],
            phone=form.get("phone") or None,
            address_line1=form["address_line1"],
            address_line2=form.get("address_line2") or None,
            city=form["city"],
            state=form.get("state") or None,
            postal_code=form["postal_code"],
            country=form["country"],
            payment_method=form["payment_method"],
            subtotal=round(subtotal, 2),
            discount=discount,
            shipping=shipping,
            tax=tax,
            coupon_code=coupon,
            total=round(grand, 2),
        )
        db.session.add(order)
        db.session.flush()  # assign order.id before creating items

        for item in current_user.cart_items.all():
            product = item.product
            db.session.add(OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                price=product.price,
            ))
            # Log a "purchase" to feed the recommendation engine.
            db.session.add(UserActivity(
                user_id=current_user.id, product_id=product.id, action_type="purchase"
            ))

        # Empty the cart and clear the applied coupon.
        Cart.query.filter_by(user_id=current_user.id).delete()
        from flask import session

        session.pop("coupon", None)
        db.session.commit()

        return redirect(url_for("order.order_success", order_id=order.id))

    return render_template(
        "checkout.html",
        form=form,
        rows=rows,
        subtotal=subtotal,
        discount=discount,
        shipping=shipping,
        tax=tax,
        grand=grand,
        coupon=coupon,
        tax_rate=TAX_RATE,
        payment_methods=PAYMENT_METHODS,
        indian_states=INDIAN_STATES,
    )


@order_bp.route("/success/<int:order_id>", methods=["GET"])
@login_required
def order_success(order_id):
    """Dedicated order-success page shown right after checkout."""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:  # owners only
        abort(404)

    order_items = order.items.all()
    items = [
        {"product": oi.product, "quantity": oi.quantity, "price": oi.price,
         "line_total": oi.quantity * oi.price}
        for oi in order_items
    ]

    # "Customers Also Bought" — top-rated products in the purchased categories.
    purchased_ids = [oi.product_id for oi in order_items]
    categories = [oi.product.category for oi in order_items if oi.product]
    also_bought_items = also_bought(limit=4, categories=categories, exclude=purchased_ids)

    return render_template(
        "order_success.html",
        order=order,
        items=items,
        also_bought=also_bought_items,
    )


@order_bp.route("/", methods=["GET"])
@login_required
def orders():
    """Order history for the signed-in user, newest first."""
    from sqlalchemy.orm import joinedload

    user_orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    # Batch-load every item (+ its product) for all orders in two queries,
    # avoiding the per-order N+1 that lazy `order.items` would cause.
    if user_orders:
        order_ids = [o.id for o in user_orders]
        items = (
            OrderItem.query.filter(OrderItem.order_id.in_(order_ids))
            .options(joinedload(OrderItem.product))
            .all()
        )
        grouped = {}
        for oi in items:
            grouped.setdefault(oi.order_id, []).append(oi)
        for o in user_orders:
            o._items = grouped.get(o.id, [])

    return render_template("orders.html", orders=user_orders)


@order_bp.route("/<int:order_id>", methods=["GET"])
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:  # owners only
        abort(404)

    items = [
        {"product": oi.product, "quantity": oi.quantity, "price": oi.price,
         "line_total": oi.quantity * oi.price}
        for oi in order.items.all()
    ]
    return render_template(
        "order_detail.html", order=order, items=items,
        confirmed=request.args.get("confirmed"),
    )
