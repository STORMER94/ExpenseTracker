from flask import render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
from sqlalchemy import extract, func
import json
import calendar

from app import app, db
from models import User, Transaction, Category
from forms import (RegistrationForm, LoginForm, TransactionForm, CategoryForm, 
                  TransactionFilterForm, ChangePasswordForm, ProfileUpdateForm)

# Context processor to provide utility functions to templates
@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    return dict(now=now)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    # Get fiscal years for filter
    fiscal_years = db.session.query(Transaction.fiscal_year).filter_by(user_id=current_user.id).distinct().all()
    fiscal_years = [year[0] for year in fiscal_years]
    
    # If no fiscal years found (new user), use current year
    if not fiscal_years:
        current_year = datetime.now().year
        fiscal_years = [current_year]
    
    # Default to the most recent fiscal year
    selected_year = request.args.get('fy', type=int) or max(fiscal_years)
    selected_month = request.args.get('month', type=int) or 0
    
    # Create the filter form
    filter_form = TransactionFilterForm()
    filter_form.fiscal_year.choices = [(year, f"FY {year}") for year in fiscal_years]
    filter_form.fiscal_year.default = selected_year
    filter_form.month.default = selected_month
    
    # Get filtered transactions
    query = Transaction.query.filter_by(user_id=current_user.id, fiscal_year=selected_year)
    
    if selected_month > 0:
        query = query.filter_by(month=selected_month)
    
    # Get recent transactions
    recent_transactions = query.order_by(Transaction.date.desc()).limit(5).all()
    
    # Calculate totals for different transaction types
    debit_query = query.filter_by(transaction_type='debit')
    credit_query = query.filter_by(transaction_type='credit')
    
    total_debits = debit_query.with_entities(func.sum(Transaction.amount)).scalar() or 0
    total_credits = credit_query.with_entities(func.sum(Transaction.amount)).scalar() or 0
    
    # Count total transactions
    transaction_count = query.count()
    
    # Get data for charts
    category_data = get_transactions_by_category(selected_year, selected_month)
    monthly_data = get_transactions_by_month(selected_year)
    credit_debit_data = get_credit_vs_debit(selected_year, selected_month)
    
    return render_template('home.html', 
                          recent_transactions=recent_transactions,
                          total_debits=total_debits,
                          total_credits=total_credits,
                          transaction_count=transaction_count,
                          filter_form=filter_form,
                          category_data=json.dumps(category_data),
                          monthly_data=json.dumps(monthly_data),
                          credit_debit_data=json.dumps(credit_debit_data),
                          selected_year=selected_year,
                          selected_month=selected_month)

def get_transactions_by_category(year, month=0):
    """Get transaction data grouped by category for charts"""
    # Query for debit transactions
    debit_query = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Category).filter(
        Transaction.user_id == current_user.id,
        Transaction.fiscal_year == year,
        Transaction.transaction_type == 'debit'
    )
    
    if month > 0:
        debit_query = debit_query.filter(Transaction.month == month)
        
    debit_data = debit_query.group_by(Category.name).all()
    
    # Query for credit transactions
    credit_query = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label('total')
    ).join(Category).filter(
        Transaction.user_id == current_user.id,
        Transaction.fiscal_year == year,
        Transaction.transaction_type == 'credit'
    )
    
    if month > 0:
        credit_query = credit_query.filter(Transaction.month == month)
        
    credit_data = credit_query.group_by(Category.name).all()
    
    return {
        'debit_labels': [item[0] for item in debit_data],
        'debit_values': [float(item[1]) for item in debit_data],
        'credit_labels': [item[0] for item in credit_data],
        'credit_values': [float(item[1]) for item in credit_data]
    }

def get_transactions_by_month(year):
    """Get transaction data grouped by month for charts"""
    # Query for debit transactions by month
    debit_query = db.session.query(
        Transaction.month,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.fiscal_year == year,
        Transaction.transaction_type == 'debit'
    ).group_by(Transaction.month).order_by(Transaction.month).all()
    
    # Query for credit transactions by month
    credit_query = db.session.query(
        Transaction.month,
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.fiscal_year == year,
        Transaction.transaction_type == 'credit'
    ).group_by(Transaction.month).order_by(Transaction.month).all()
    
    # Create a list with all months
    all_months = [(i, 0, 0) for i in range(1, 13)]  # (month, debit, credit)
    
    # Fill in the debit data
    for month, total in debit_query:
        all_months[month-1] = (month, float(total), all_months[month-1][2])
    
    # Fill in the credit data
    for month, total in credit_query:
        all_months[month-1] = (month, all_months[month-1][1], float(total))
    
    return {
        'labels': [calendar.month_name[month] for month, _, _ in all_months],
        'debit_values': [debit for _, debit, _ in all_months],
        'credit_values': [credit for _, _, credit in all_months]
    }

def get_credit_vs_debit(year, month=0):
    """Get credit vs debit totals for pie chart"""
    # Get total debit transactions
    debit_query = Transaction.query.filter_by(
        user_id=current_user.id,
        fiscal_year=year,
        transaction_type='debit'
    )
    
    # Get total credit transactions
    credit_query = Transaction.query.filter_by(
        user_id=current_user.id,
        fiscal_year=year,
        transaction_type='credit'
    )
    
    if month > 0:
        debit_query = debit_query.filter_by(month=month)
        credit_query = credit_query.filter_by(month=month)
        
    total_debits = debit_query.with_entities(func.sum(Transaction.amount)).scalar() or 0
    total_credits = credit_query.with_entities(func.sum(Transaction.amount)).scalar() or 0
    
    return {
        'labels': ['Debits (Money Out)', 'Credits (Money In)'],
        'values': [float(total_debits), float(total_credits)]
    }

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # Create default categories for the new user
        default_categories = [
            ('Food & Dining', 'Restaurants, groceries, and food delivery'),
            ('Transportation', 'Gas, public transit, and vehicle expenses'),
            ('Housing', 'Rent, mortgage, and home maintenance'),
            ('Utilities', 'Electric, water, gas, and internet bills'),
            ('Entertainment', 'Movies, games, and leisure activities'),
            ('Healthcare', 'Medical expenses and health insurance'),
            ('Shopping', 'Clothing, electronics, and personal items'),
            ('Travel', 'Flights, hotels, and vacation expenses'),
            ('Education', 'Tuition, books, and courses'),
            ('Income', 'Salary, freelance work, and other income'),
            ('Other', 'Miscellaneous transactions')
        ]
        
        for name, description in default_categories:
            category = Category(name=name, description=description, user_id=user.id)
            db.session.add(category)
        
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful.', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check your username and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm(current_user.email)
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data
        
        db.session.commit()
        
        flash('Your profile has been updated!', 'success')
        return redirect(url_for('profile'))
    
    # Pre-populate the form
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    
    return render_template('profile.html', form=form)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            
            flash('Your password has been updated!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Current password is incorrect.', 'danger')
    
    return render_template('change_password.html', form=form)

@app.route('/categories')
@login_required
def categories():
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def add_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            user_id=current_user.id
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category has been added!', 'success')
        return redirect(url_for('categories'))
    
    return render_template('add_category.html', form=form)

@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Ensure the user owns this category
    if category.user_id != current_user.id:
        flash('You are not authorized to edit this category.', 'danger')
        return redirect(url_for('categories'))
    
    form = CategoryForm()
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        
        db.session.commit()
        
        flash('Category has been updated!', 'success')
        return redirect(url_for('categories'))
    
    # Pre-populate the form with current category data
    if request.method == 'GET':
        form.name.data = category.name
        form.description.data = category.description
    
    return render_template('edit_category.html', form=form, category=category)

@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Ensure the user owns this category
    if category.user_id != current_user.id:
        flash('You are not authorized to delete this category.', 'danger')
        return redirect(url_for('categories'))
    
    # Check if category is in use
    if Transaction.query.filter_by(category_id=category.id).first():
        flash('Cannot delete category that is in use by transactions.', 'danger')
        return redirect(url_for('categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category has been deleted!', 'success')
    return redirect(url_for('categories'))

@app.route('/transactions')
@login_required
def transactions():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Query transactions with joined category data for more efficient access
    transactions = Transaction.query.filter_by(user_id=current_user.id).join(
        Category, Transaction.category_id == Category.id).order_by(
        Transaction.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('transactions.html', transactions=transactions)

@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    # Check if user has categories
    if not Category.query.filter_by(user_id=current_user.id).first():
        flash('You need to create at least one category before adding transactions.', 'warning')
        return redirect(url_for('add_category'))
    
    form = TransactionForm(current_user)
    
    if form.validate_on_submit():
        # Calculate fiscal year and month
        transaction_date = form.date.data
        fiscal_year = transaction_date.year
        month = transaction_date.month
        
        transaction = Transaction(
            amount=form.amount.data,
            date=transaction_date,
            transaction_type=form.transaction_type.data,
            category_id=form.category_id.data,
            description=form.description.data,
            user_id=current_user.id,
            fiscal_year=fiscal_year,
            month=month
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction has been added!', 'success')
        return redirect(url_for('transactions'))
    
    return render_template('add_transaction.html', form=form)

@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Ensure the user owns this transaction
    if transaction.user_id != current_user.id:
        flash('You are not authorized to edit this transaction.', 'danger')
        return redirect(url_for('transactions'))
    
    form = TransactionForm(current_user)
    
    if form.validate_on_submit():
        # Calculate fiscal year and month (in case date changed)
        transaction_date = form.date.data
        fiscal_year = transaction_date.year
        month = transaction_date.month
        
        transaction.amount = form.amount.data
        transaction.date = transaction_date
        transaction.transaction_type = form.transaction_type.data
        transaction.category_id = form.category_id.data
        transaction.description = form.description.data
        transaction.fiscal_year = fiscal_year
        transaction.month = month
        
        db.session.commit()
        
        flash('Transaction has been updated!', 'success')
        return redirect(url_for('transactions'))
    
    # Pre-populate the form with current transaction data
    if request.method == 'GET':
        form.amount.data = transaction.amount
        form.date.data = transaction.date
        form.transaction_type.data = transaction.transaction_type
        form.category_id.data = transaction.category_id
        form.description.data = transaction.description
    
    return render_template('edit_transaction.html', form=form, transaction=transaction)

@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Ensure the user owns this transaction
    if transaction.user_id != current_user.id:
        flash('You are not authorized to delete this transaction.', 'danger')
        return redirect(url_for('transactions'))
    
    db.session.delete(transaction)
    db.session.commit()
    
    flash('Transaction has been deleted!', 'success')
    return redirect(url_for('transactions'))