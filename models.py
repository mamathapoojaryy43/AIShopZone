"""SQLAlchemy models for AIShopzone."""
from datetime import datetime

from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(191), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", back_populates="user", lazy="dynamic")
    cart_items = db.relationship(
        "Cart", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    wishlist_items = db.relationship(
        "Wishlist",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    activities = db.relationship(
        "UserActivity",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(191), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(512), nullable=True)
    rating = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.Text, nullable=True)

    cart_items = db.relationship(
        "Cart", back_populates="product", lazy="dynamic", cascade="all, delete-orphan"
    )
    wishlist_items = db.relationship(
        "Wishlist", back_populates="product", lazy="dynamic", cascade="all, delete-orphan"
    )
    order_items = db.relationship("OrderItem", back_populates="product", lazy="dynamic")
    activities = db.relationship(
        "UserActivity", back_populates="product", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Product {self.name}>"


class Order(db.Model):
    __tablename__ = "order"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(40), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ----- Shipping / contact details captured at checkout -----
    full_name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(191), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    address_line1 = db.Column(db.String(255), nullable=True)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    state = db.Column(db.String(120), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    payment_method = db.Column(db.String(40), nullable=True)

    # ----- Pricing snapshot at time of purchase -----
    subtotal = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    shipping = db.Column(db.Float, default=0.0)
    tax = db.Column(db.Float, default=0.0)
    coupon_code = db.Column(db.String(40), nullable=True)

    user = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem", back_populates="order", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Order {self.id} status={self.status}>"


class OrderItem(db.Model):
    __tablename__ = "order_item"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.id} product={self.product_id}>"


class Cart(db.Model):
    __tablename__ = "cart"
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    user = db.relationship("User", back_populates="cart_items")
    product = db.relationship("Product", back_populates="cart_items")

    def __repr__(self):
        return f"<Cart user={self.user_id} product={self.product_id}>"


class Wishlist(db.Model):
    __tablename__ = "wishlist"
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="wishlist_items")
    product = db.relationship("Product", back_populates="wishlist_items")

    def __repr__(self):
        return f"<Wishlist user={self.user_id} product={self.product_id}>"


class UserActivity(db.Model):
    __tablename__ = "user_activity"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    action_type = db.Column(db.String(40), nullable=False)  # view | purchase | wishlist
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="activities")
    product = db.relationship("Product", back_populates="activities")

    def __repr__(self):
        return f"<UserActivity {self.action_type} product={self.product_id}>"
