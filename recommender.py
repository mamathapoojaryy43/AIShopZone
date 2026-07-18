"""Recommendation engine for AIShopzone.

Combines a fast, local heuristic recommender (category/affinity based on a
user's stored activity) with an optional LLM call (OpenAI or Claude) that
receives the user's activity and the product catalog and returns product ids.

The LLM is attempted first when an API key is configured; on any failure
(missing key, network error, timeout, unparseable response) we fall back to
the heuristic so recommendations always render.
"""
import json
import urllib.request

from extensions import db
from models import Product, UserActivity

# Seconds to wait for an LLM response before falling back to the heuristic.
LLM_TIMEOUT = 4.0


def user_activity(user_id):
    """Return {action: [product_id, ...]} for the user's recent activity."""
    rows = (
        UserActivity.query.filter_by(user_id=user_id)
        .order_by(UserActivity.created_at.desc())
        .all()
    )
    activity = {"view": [], "purchase": [], "wishlist": []}
    for r in rows:
        if r.action_type in activity:
            activity[r.action_type].append(r.product_id)
    return activity


def interacted_ids(user_id):
    """All product ids the user has viewed / purchased / wishlisted."""
    ids = set()
    for lst in user_activity(user_id).values():
        ids.update(lst)
    return ids


def popular_products(limit=8, exclude=None, offset=0):
    """Top-rated products overall (used for guests / global sections)."""
    q = Product.query
    if exclude:
        q = q.filter(Product.id.notin_(exclude))
    return q.order_by(Product.rating.desc()).offset(offset).limit(limit).all()


def also_bought(limit=8, categories=None, exclude=None):
    """Products in the given categories (or globally), highest rated first."""
    q = Product.query
    if categories:
        q = q.filter(Product.category.in_(categories))
    if exclude:
        q = q.filter(Product.id.notin_(exclude))
    return q.order_by(Product.rating.desc()).limit(limit).all()


def heuristic_recommendations(user_id, limit=8):
    """Local recommender: bias toward categories the user engaged with."""
    seen = interacted_ids(user_id)
    acts = user_activity(user_id)

    # Batch-load every engaged product in a single query (avoids N+1).
    engaged_ids = set()
    for lst in acts.values():
        engaged_ids.update(lst)
    prods = (
        {p.id: p for p in Product.query.filter(Product.id.in_(engaged_ids)).all()}
        if engaged_ids else {}
    )

    # Categories the user cares about, weighted by action strength.
    cat_weight = {}
    for action, weight in (("purchase", 3), ("wishlist", 2), ("view", 1)):
        for pid in acts.get(action, []):
            prod = prods.get(pid)
            if prod:
                cat_weight[prod.category] = cat_weight.get(prod.category, 0) + weight

    if cat_weight:
        cats = [c for c, _ in sorted(cat_weight.items(), key=lambda x: -x[1])]
        candidates = (
            Product.query.filter(Product.category.in_(cats), Product.id.notin_(seen))
            .order_by(Product.rating.desc())
            .limit(limit)
            .all()
        )
    else:
        candidates = []

    # Fill remaining slots with globally popular products.
    if len(candidates) < limit:
        seen2 = {c.id for c in candidates}
        seen2.update(seen)
        for p in popular_products(limit, exclude=seen2):
            if p.id not in seen2:
                candidates.append(p)
            if len(candidates) >= limit:
                break
    return candidates[:limit]


def _catalog_prompt(activity, catalog, limit):
    def names(ids):
        if not ids:
            return "none"
        prods = {p.id: p for p in Product.query.filter(Product.id.in_(ids[:8])).all()}
        out = [f"{prods[i].name} ({prods[i].category})" for i in ids[:8] if i in prods]
        return ", ".join(out) if out else "none"

    catalog_json = json.dumps(
        [{"id": p["id"], "name": p["name"], "category": p["category"], "price": p["price"]}
         for p in catalog],
        ensure_ascii=False,
    )
    return (
        "You are a shopping recommendation engine for AIShopzone, an Indian "
        "e-commerce store. Recommend products for a customer based on their "
        "recent activity.\n\n"
        f"Viewed: {names(activity.get('view', []))}\n"
        f"Purchased: {names(activity.get('purchase', []))}\n"
        f"Wishlisted: {names(activity.get('wishlist', []))}\n\n"
        "CATALOG (available products):\n" + catalog_json + "\n\n"
        f"Return a JSON array of up to {limit} product ids from the CATALOG that "
        "this customer is most likely to want next. Only include ids present in "
        "the CATALOG. Respond with ONLY the JSON array, no extra text."
    )


def _parse_ids(text):
    try:
        start, end = text.find("["), text.rfind("]")
        if start != -1 and end != -1:
            return [int(x) for x in json.loads(text[start:end + 1])]
    except (ValueError, TypeError, json.JSONDecodeError):
        pass
    return []


def _call_openai(prompt, api_key, model):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _call_claude(prompt, api_key, model):
    body = json.dumps({
        "model": model,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["content"][0]["text"]


def llm_recommendations(user_id, limit=8):
    """Call the configured LLM. Return list[Product] or None on any failure."""
    from flask import current_app

    cfg = current_app.config
    provider = (cfg.get("AI_PROVIDER") or "openai").lower()
    api_key = (cfg.get("AI_API_KEY") or "").strip()
    model = cfg.get("AI_MODEL") or "gpt-4o-mini"
    # Treat the shipped placeholder / example keys as "no key configured" so we
    # never fire a doomed network request (which would block the request thread
    # for the full timeout before falling back to the heuristic).
    if not api_key or api_key.lower() in ("your-api-key-here", "change-me", "sk-your-key-here"):
        return None

    catalog = [
        {"id": p.id, "name": p.name, "category": p.category, "price": p.price}
        for p in Product.query.order_by(Product.rating.desc()).limit(40).all()
    ]
    if not catalog:
        return None

    prompt = _catalog_prompt(user_activity(user_id), catalog, limit)
    try:
        if provider == "claude":
            text = _call_claude(prompt, api_key, model)
        else:
            text = _call_openai(prompt, api_key, model)
    except Exception:
        return None

    ids = _parse_ids(text)
    if not ids:
        return None

    # Batch-load the recommended products in one query.
    wanted = list(dict.fromkeys(ids))[:limit]
    prods = {p.id: p for p in Product.query.filter(Product.id.in_(wanted)).all()}
    products = [prods[pid] for pid in wanted if pid in prods]
    return products or None


def recommend_for_user(user_id, limit=8, try_llm=True):
    """Return (products, source) where source is 'llm' or 'heuristic'."""
    if try_llm:
        products = llm_recommendations(user_id, limit)
        if products:
            return products, "llm"
    return heuristic_recommendations(user_id, limit), "heuristic"
