"""AIShopzone application factory.

Run with:

    flask --app app run --debug

or simply:

    python app.py
"""
import os

from flask import Flask, render_template, url_for
from flask_login import current_user
from config import config_map
from extensions import db, login_manager
from models import User

from routes import (
    auth_bp,
    product_bp,
    cart_bp,
    order_bp,
    admin_bp,
    ai_bp,
)


def create_app(config_name=None):
    """Build and return the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map[config_name])

    # Initialise extensions with this app instance.
    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Helper for templates: is a blueprint (or its routes) registered yet?
    def has_endpoint(prefix):
        eps = {rule.endpoint for rule in app.url_map.iter_rules()}
        return prefix in eps or any(
            ep.startswith(prefix + ".") for ep in eps
        )

    app.jinja_env.globals["has_endpoint"] = has_endpoint

    # ----- Image fallback system -----
    from utils import product_image_url, category_image_url, product_gallery

    app.jinja_env.globals["product_image_url"] = product_image_url
    app.jinja_env.globals["category_image_url"] = category_image_url
    app.jinja_env.globals["product_gallery"] = product_gallery

    # ----- Currency formatting (INR) -----
    from flask import current_app

    def money(value):
        try:
            return f"{current_app.config.get('CURRENCY_SYMBOL', '₹')}{float(value):,.2f}"
        except (TypeError, ValueError):
            return ""

    def money0(value):
        try:
            return f"{current_app.config.get('CURRENCY_SYMBOL', '₹')}{float(value):,.0f}"
        except (TypeError, ValueError):
            return ""

    app.jinja_env.filters["money"] = money
    app.jinja_env.filters["money0"] = money0

    # Cart + wishlist counts for the header badges (authenticated users only).
    @app.context_processor
    def inject_cart_count():
        cart_count = 0
        wishlist_count = 0
        if current_user.is_authenticated:
            from models import Cart, Wishlist
            from sqlalchemy import func

            cart_count = (
                db.session.query(func.coalesce(func.sum(Cart.quantity), 0))
                .filter(Cart.user_id == current_user.id)
                .scalar()
                or 0
            )
            wishlist_count = Wishlist.query.filter_by(user_id=current_user.id).count()
        return {"cart_count": cart_count, "wishlist_count": wishlist_count}

    # Register blueprints.
    app.register_blueprint(auth_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)

    # Simple error pages.
    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("404.html"), 404

    @app.context_processor
    def inject_admin_flag():
        is_admin = (
            current_user.is_authenticated
            and current_user.email == app.config.get("ADMIN_EMAIL")
        )
        return {"is_admin": is_admin}

    # Wishlisted product ids for the signed-in user, so the heart on product
    # cards / the PDP can show its "saved" state on first paint (no JS round-trip).
    @app.context_processor
    def inject_wishlist_ids():
        ids = set()
        if current_user.is_authenticated:
            ids = {w.product_id for w in current_user.wishlist_items.all()}
        return {"wishlist_ids": ids}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
