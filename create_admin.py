"""Create or update the admin user account.

Run once:
    python create_admin.py
"""
from app import app
from extensions import db
from models import User

ADMIN_EMAIL = "host@aishopzone.com"
ADMIN_NAME = "host"
ADMIN_PASSWORD = "host123"

with app.app_context():
    db.create_all()
    user = User.query.filter_by(email=ADMIN_EMAIL).first()
    if user:
        user.set_password(ADMIN_PASSWORD)
        user.name = ADMIN_NAME
        print(f"Updated existing admin account: {ADMIN_EMAIL}")
    else:
        user = User(name=ADMIN_NAME, email=ADMIN_EMAIL)
        user.set_password(ADMIN_PASSWORD)
        db.session.add(user)
        print(f"Created new admin account: {ADMIN_EMAIL}")
    db.session.commit()
    print("Done! You can now log in at /auth/login")
    print(f"  Email   : {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
