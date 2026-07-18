"""Blueprint package for AIShopzone route modules."""
from routes.auth_routes import auth_bp
from routes.product_routes import product_bp
from routes.cart_routes import cart_bp
from routes.order_routes import order_bp
from routes.admin_routes import admin_bp
from routes.ai_routes import ai_bp

__all__ = [
    "auth_bp",
    "product_bp",
    "cart_bp",
    "order_bp",
    "admin_bp",
    "ai_bp",
]
