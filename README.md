# 🛍️ AIShopzone

AIShopzone is a modern AI-powered e-commerce platform built with **Flask**, **MySQL**, and **SQLAlchemy**. It provides a complete online shopping experience with secure authentication, shopping cart, checkout, order management, an admin dashboard, and intelligent product recommendations powered by Large Language Models (LLMs).

Designed as a production-style full-stack project, AIShopzone demonstrates backend development, database management, authentication, AI integration, and responsive frontend design.

---

## ✨ Features

### 👤 User Features

- User Registration & Login
- Secure Authentication using Flask-Login
- Browse Products by Category
- Product Search
- Product Details Page
- AI-Powered Product Recommendations
- Shopping Cart
- Wishlist
- Checkout System
- Order History
- User Profile
- Indian Currency (₹)
- GST-ready Pricing
- UPI-Friendly Checkout Flow

---

### 🤖 AI Features

- AI-generated product recommendations
- Personalized shopping suggestions
- Supports OpenAI or Claude APIs
- Optional AI key (application works without AI)

---

### 🛠 Admin Features

- Secure Admin Login
- Dashboard Analytics
- Product Management (CRUD)
- Category Management
- User Management
- Order Management
- Inventory Tracking
- Sales Statistics

---

## 🏗 Tech Stack

| Layer | Technology |
|--------|------------|
| Backend | Flask |
| Language | Python 3 |
| Database | MySQL |
| ORM | SQLAlchemy |
| Authentication | Flask-Login |
| Frontend | HTML5, CSS3, JavaScript |
| Templates | Jinja2 |
| AI | OpenAI / Claude API |
| Version Control | Git & GitHub |

---

## 📂 Project Structure

```
AIShopzone/
│
├── app.py
├── config.py
├── models.py
├── extensions.py
├── requirements.txt
├── seed_data.py
├── generate_product_images.py
├── create_admin.py
├── .env.example
│
├── routes/
│   ├── auth_routes.py
│   ├── product_routes.py
│   ├── cart_routes.py
│   ├── order_routes.py
│   ├── admin_routes.py
│   └── ai_routes.py
│
├── templates/
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── README.md
```

---

# 🚀 Installation

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/AIShopzone.git

cd AIShopzone
```

---

## 2. Create Virtual Environment

Windows

```bash
python -m venv venv

venv\Scripts\activate
```

Linux / macOS

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Copy

```
.env.example
```

to

```
.env
```

and configure:

```
SECRET_KEY=your_secret_key

DB_HOST=localhost
DB_PORT=3306
DB_NAME=aishopzone
DB_USER=root
DB_PASSWORD=your_password

OPENAI_API_KEY=your_key
# OR
CLAUDE_API_KEY=your_key
```

---

## 5. Create Database

```sql
CREATE DATABASE aishopzone CHARACTER SET utf8mb4;
```

---

## 6. Seed Demo Data

```bash
python seed_data.py
```

To reset existing demo data:

```bash
python seed_data.py --reset
```

---

## 7. Generate Product Images (Optional)

```bash
python generate_product_images.py
```

---

## 8. Create Admin Account

```bash
python create_admin.py
```

Example credentials:

```
Email:
host@aishopzone.com

Password:
host123
```

---

## 9. Run the Application

```bash
flask --app app run --debug
```

Application URL

```
http://127.0.0.1:5000
```

---

# 👨‍💼 Admin Panel

Admin dashboard includes:

- Dashboard Analytics
- Product Management
- Category Management
- Order Management
- User Management
- Inventory Monitoring

Access:

```
/admin
```

---

# 🤖 AI Recommendation Engine

AIShopzone supports:

- OpenAI
- Claude

If no API key is configured, the application continues to function with standard shopping features.

---

# 📸 Screenshots

You can add screenshots here.

Example:

```
screenshots/
├── home.png
├── products.png
├── cart.png
├── checkout.png
├── admin-dashboard.png
```

---

# 📈 Future Improvements

- Product Reviews
- Coupons & Discounts
- Razorpay Integration
- Email Notifications
- Payment Gateway
- Product Ratings
- AI Chat Shopping Assistant
- Multi-vendor Marketplace
- Recommendation Personalization

---

# 🤝 Contributing

Contributions are welcome!

1. Fork the repository

2. Create a feature branch

```bash
git checkout -b feature-name
```

3. Commit changes

```bash
git commit -m "Add new feature"
```

4. Push

```bash
git push origin feature-name
```

5. Open a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

---

# ⭐ Support

If you found this project useful, please consider giving it a ⭐ on GitHub.
