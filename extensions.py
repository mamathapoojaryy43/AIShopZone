"""Shared Flask extensions.

These are created once here and initialised inside the app factory so the
application can be created multiple times (e.g. for tests) without
module-level side effects.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
