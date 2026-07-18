# AIShopzone

A production-quality e-commerce platform built with Flask, MySQL, and an
LLM-powered recommendation engine.

## Tech Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Login
- **Database:** MySQL (via PyMySQL)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Jinja2
- **AI:** OpenAI / Claude API for product recommendations

## Project Structure

```
AIShopzone/
├── app.py                  # Application factory & entry point
├── config.py               # Configuration (dev / prod)
├── extensions.py           # Shared Flask extensions
├── models.py               # SQLAlchemy models
├── seed_data.py            # Demo data loader
├── requirements.txt
├── .env.example
├── routes/                 # Blueprint route modules
│   ├── auth_routes.py
│   ├── product_routes.py
│   ├── cart_routes.py
│   ├── order_routes.py
│   ├── admin_routes.py
│   └── ai_routes.py
├── templates/              # Jinja2 templates
└── static/                 # CSS, JS, images
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   venv\Scripts\activate    # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your MySQL credentials and
   AI API key.

4. Create the database in MySQL:

   ```sql
   CREATE DATABASE aishopzone CHARACTER SET utf8mb4;
   ```

5. Run the app:

   ```bash
   flask --app app run --debug
   ```

## Current Status

- **Step 1 — Project scaffold:** Flask app, MySQL config, SQLAlchemy,
  Flask-Login, blueprints, base template, and static folders are in place.
- **Step 2 — Products & catalog:** Browse, search, filter, sort, paginate,
  product detail page with reviews, related items, recently viewed, and a
  heuristic recommender (`routes/product_routes.py`).
- **Step 3 — Shopping cart:** Add / update / remove / coupon, with shipping,
  tax, and free-shipping-threshold logic (`routes/cart_routes.py`).
- **Step 4 — Authentication:** Login, signup, logout, and password-recovery
  stub with open-redirect protection (`routes/auth_routes.py`).
- **Step 5 — Checkout & orders (latest):** Two-column responsive checkout with
  shipping address + **mock credit-card** payment (card data is never stored),
  plus an order-success page, order history, and order detail. Ownership-guarded
  (`routes/order_routes.py`, templates `checkout.html`, `order_success.html`,
  `orders.html`, `order_detail.html`).

- **Step 6 — AI recommendations:** Activity (view / purchase / wishlist) is
  stored per user in `UserActivity`. `recommender.py` sends that activity + the
  product catalog to the configured LLM (OpenAI or Claude, via `urllib` — no
  extra SDK) and returns recommended product ids; on any failure (no key,
  network error, timeout, bad response) it falls back to a local heuristic so
  recommendations always render. Exposed as `GET /api/recommendations/<user_id>`
  (`routes/ai_routes.py`, owner-only). Surfaced on the **homepage**
  (Recommended For You + Customers Also Bought), **product detail**
  (Recommended For You + Customers Also Bought + Recently Viewed), and
  **order success** (Customers Also Bought).

### Localization (India)

Currency is **Indian Rupees (₹)** with thousands separators, rendered via a
central `money` / `money0` Jinja filter (`app.py`). Pricing defaults live in
`routes/cart_routes.py`: **18% GST**, **₹49 flat shipping**, **free shipping
over ₹499**. The checkout is localized for India — default country "India",
a State/UT dropdown, 6-digit PIN code, `+91` phone, and **UPI** as a payment
option (replacing PayPal); card details remain mock-only and are never stored.
Brand/contact details (Bangalore address, +91 phone, RuPay/UPI/COD badges)
are set in `templates/base.html`.

### Next up (stub pending)

- **Admin panel** — manage products and orders (`routes/admin_routes.py`).
