from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)  # Added field for first name
    last_name = db.Column(db.String(64), nullable=False)   # Added field for last name
    expenses = db.relationship('Expense', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expenses = db.relationship('Expense', backref='category_info', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Title field has been removed
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Now using a foreign key to the Category table
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Adding fields to support filters
    fiscal_year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<Expense ${self.amount:.2f} - {self.description}>'
