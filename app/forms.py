from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField, FileField, RadioField, SelectMultipleField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from app import db
import sqlalchemy as sa
from app.models import User, Puzzle

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
    # PasswordInput?
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
        
class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    # make sure to check that user is not changing their current username to another already in db
    def check_username_available(self, username):
        if username != current_user.username:
            user = User.query.filter_by(username=username).first()
            # return True or False
            return user 

class CreatePuzzleForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    pieces = StringField('Pieces', validators=[DataRequired()])
    condition = RadioField('Condition', validators=[DataRequired()])
    manufacturer = StringField('Manufacturer', validators=[DataRequired()])
    # ***add FileAllowed extensions
    image = FileField('Image', validators=[FileRequired()])
    # category_id = SelectField('Category', validators=[DataRequired()])
    categories = SelectMultipleField('Categories')
    description = TextAreaField('Additional Notes', validators=[Length(min=0, max=140)])
    submit = SubmitField('Post Your Puzzle')



