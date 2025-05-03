from flask import render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime

from app import app, db
from models import User, Expense
from forms import RegistrationForm, LoginForm, ExpenseForm

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
    # Get recent expenses
    recent_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(5).all()
    
    # Calculate total expense amount
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0
    
    # Count total expenses
    expenses_count = Expense.query.filter_by(user_id=current_user.id).count()
    
    return render_template('home.html', 
                          recent_expenses=recent_expenses,
                          total_expenses=total_expenses,
                          expenses_count=expenses_count)

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

@app.route('/expenses')
@login_required
def expenses():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Query expenses with joined user data for more efficient access
    expenses = Expense.query.filter_by(user_id=current_user.id).join(
        User, Expense.user_id == User.id).order_by(
        Expense.date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('expenses.html', expenses=expenses)

@app.route('/expenses/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    form = ExpenseForm()
    
    if form.validate_on_submit():
        expense = Expense(
            title=form.title.data,
            amount=form.amount.data,
            date=form.date.data,
            category=form.category.data,
            description=form.description.data,
            user_id=current_user.id
        )
        
        db.session.add(expense)
        db.session.commit()
        
        flash('Expense has been added!', 'success')
        return redirect(url_for('expenses'))
    
    return render_template('add_expense.html', form=form)

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
