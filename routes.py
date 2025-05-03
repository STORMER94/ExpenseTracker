from flask import render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
from sqlalchemy import extract, func
import json
import calendar

from app import app, db
from models import User, Expense, Category
from forms import RegistrationForm, LoginForm, ExpenseForm, CategoryForm, ExpenseFilterForm

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
    fiscal_years = db.session.query(Expense.fiscal_year).filter_by(user_id=current_user.id).distinct().all()
    fiscal_years = [year[0] for year in fiscal_years]
    
    # If no fiscal years found (new user), use current year
    if not fiscal_years:
        current_year = datetime.now().year
        fiscal_years = [current_year]
    
    # Default to the most recent fiscal year
    selected_year = request.args.get('fy', type=int) or max(fiscal_years)
    selected_month = request.args.get('month', type=int) or 0
    
    # Create the filter form
    filter_form = ExpenseFilterForm()
    filter_form.fiscal_year.choices = [(year, f"FY {year}") for year in fiscal_years]
    filter_form.fiscal_year.default = selected_year
    filter_form.month.default = selected_month
    
    # Get filtered expenses
    query = Expense.query.filter_by(user_id=current_user.id, fiscal_year=selected_year)
    
    if selected_month > 0:
        query = query.filter_by(month=selected_month)
    
    # Get recent expenses
    recent_expenses = query.order_by(Expense.date.desc()).limit(5).all()
    
    # Calculate total expense amount for the filter
    total_expenses = query.with_entities(func.sum(Expense.amount)).scalar() or 0
    
    # Count total expenses for the filter
    expenses_count = query.count()
    
    # Get expense data for charts
    category_data = get_expense_by_category(selected_year, selected_month)
    monthly_data = get_expense_by_month(selected_year)
    
    return render_template('home.html', 
                          recent_expenses=recent_expenses,
                          total_expenses=total_expenses,
                          expenses_count=expenses_count,
                          filter_form=filter_form,
                          category_data=json.dumps(category_data),
                          monthly_data=json.dumps(monthly_data),
                          selected_year=selected_year,
                          selected_month=selected_month)

def get_expense_by_category(year, month=0):
    """Get expense data grouped by category for charts"""
    query = db.session.query(
        Category.name,
        func.sum(Expense.amount).label('total')
    ).join(Category).filter(
        Expense.user_id == current_user.id,
        Expense.fiscal_year == year
    )
    
    if month > 0:
        query = query.filter(Expense.month == month)
        
    data = query.group_by(Category.name).all()
    
    return {
        'labels': [item[0] for item in data],
        'values': [float(item[1]) for item in data]
    }

def get_expense_by_month(year):
    """Get expense data grouped by month for charts"""
    query = db.session.query(
        Expense.month,
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.fiscal_year == year
    ).group_by(Expense.month).order_by(Expense.month).all()
    
    # Create a list with all months
    all_months = [(i, 0) for i in range(1, 13)]
    
    # Fill in the actual data
    for month, total in query:
        all_months[month-1] = (month, float(total))
    
    return {
        'labels': [calendar.month_name[month] for month, _ in all_months],
        'values': [total for _, total in all_months]
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
            ('Other', 'Miscellaneous expenses')
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
    if Expense.query.filter_by(category_id=category.id).first():
        flash('Cannot delete category that is in use by expenses.', 'danger')
        return redirect(url_for('categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category has been deleted!', 'success')
    return redirect(url_for('categories'))

@app.route('/expenses')
@login_required
def expenses():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Query expenses with joined user and category data for more efficient access
    expenses = Expense.query.filter_by(user_id=current_user.id).join(
        Category, Expense.category_id == Category.id).order_by(
        Expense.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('expenses.html', expenses=expenses)

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    # Check if user has categories
    if not Category.query.filter_by(user_id=current_user.id).first():
        flash('You need to create at least one category before adding expenses.', 'warning')
        return redirect(url_for('add_category'))
    
    form = ExpenseForm(current_user)
    
    if form.validate_on_submit():
        # Calculate fiscal year and month
        expense_date = form.date.data
        fiscal_year = expense_date.year
        month = expense_date.month
        
        expense = Expense(
            amount=form.amount.data,
            date=expense_date,
            category_id=form.category_id.data,
            description=form.description.data,
            user_id=current_user.id,
            fiscal_year=fiscal_year,
            month=month
        )
        
        db.session.add(expense)
        db.session.commit()
        
        flash('Expense has been added!', 'success')
        return redirect(url_for('expenses'))
    
    return render_template('add_expense.html', form=form)

@app.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    # Ensure the user owns this expense
    if expense.user_id != current_user.id:
        flash('You are not authorized to edit this expense.', 'danger')
        return redirect(url_for('expenses'))
    
    form = ExpenseForm(current_user)
    
    if form.validate_on_submit():
        # Calculate fiscal year and month (in case date changed)
        expense_date = form.date.data
        fiscal_year = expense_date.year
        month = expense_date.month
        
        expense.amount = form.amount.data
        expense.date = expense_date
        expense.category_id = form.category_id.data
        expense.description = form.description.data
        expense.fiscal_year = fiscal_year
        expense.month = month
        
        db.session.commit()
        
        flash('Expense has been updated!', 'success')
        return redirect(url_for('expenses'))
    
    # Pre-populate the form with current expense data
    if request.method == 'GET':
        form.amount.data = expense.amount
        form.date.data = expense.date
        form.category_id.data = expense.category_id
        form.description.data = expense.description
    
    return render_template('edit_expense.html', form=form, expense=expense)

@app.route('/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    # Ensure the user owns this expense
    if expense.user_id != current_user.id:
        flash('You are not authorized to delete this expense.', 'danger')
        return redirect(url_for('expenses'))
    
    db.session.delete(expense)
    db.session.commit()
    
    flash('Expense has been deleted!', 'success')
    return redirect(url_for('expenses'))
