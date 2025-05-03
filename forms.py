from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, SelectField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange
import datetime
from models import User
from app import db

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email is already registered. Please use a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ExpenseForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    date = DateField('Date', format='%Y-%m-%d', validators=[DataRequired()], default=datetime.date.today)
    category = SelectField('Category', validators=[DataRequired()], 
                          choices=[
                              ('food', 'Food & Dining'), 
                              ('transportation', 'Transportation'), 
                              ('housing', 'Housing'), 
                              ('utilities', 'Utilities'), 
                              ('entertainment', 'Entertainment'), 
                              ('healthcare', 'Healthcare'), 
                              ('shopping', 'Shopping'), 
                              ('travel', 'Travel'), 
                              ('education', 'Education'),
                              ('other', 'Other')
                          ])
    description = TextAreaField('Description', validators=[Length(max=500)])
    submit = SubmitField('Add Expense')
