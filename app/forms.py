from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app import db
import sqlalchemy as sa
from app.models import User

# first argument - description or label of field
# second arg - validators optional - DataRequired checks to make sure field is not empty 
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign in')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    # handling if username already exists in db
    def validate_username(self, username):
        # gives you 1 result that matches the username submitted from the reg form
        user = db.session.scalar(sa.select(User).where(
            User.username == username.data
        ))
        if user is not None:
            raise ValidationError('Username already exists')
    
    # handling if email already exists in db
    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(
            User.email == email.data
        ))
        if user is not None:
            raise ValidationError('Email already exists')
    