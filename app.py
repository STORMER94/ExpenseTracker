import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Define base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Configure database connection - using SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expense_tracker.db"

# Initialize database with app
db.init_app(app)

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize database tables
with app.app_context():
    # Import models here to ensure they're registered with SQLAlchemy
    from models import User, Transaction, Category
    db.create_all()

# Import user loader function
from models import User

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
