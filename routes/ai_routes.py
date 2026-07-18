"""AI recommendation routes."""
from flask import Blueprint, request, jsonify, url_for
from flask_login import login_required, current_user

from extensions import db
from models import User
from utils import product_image_url
from recommender import recommend_for_user

ai_bp = Blueprint("ai", __name__, url_prefix="/api")


def serialize_product(p):
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "price": p.price,
        "rating": p.rating,
        "image": product_image_url(p),
        "url": url_for("product.product_detail", product_id=p.id),
    }


@ai_bp.route("/recommendations/<int:user_id>", methods=["GET"])
@login_required
def recommendations(user_id):
    """Return personalized product recommendations for a user.

    Sends the user's stored activity + the product catalog to the configured
    LLM (OpenAI or Claude); falls back to a local heuristic on any failure.
    A user may only fetch their own recommendations.
    """
    if current_user.id != user_id:
        return jsonify({"error": "forbidden"}), 403

    User.query.get_or_404(user_id)
    limit = request.args.get("limit", 8, type=int)

    products, source = recommend_for_user(user_id, limit, try_llm=True)

    return jsonify({
        "user_id": user_id,
        "source": source,
        "count": len(products),
        "products": [serialize_product(p) for p in products],
    })
