from app import app, db
from flask import render_template, flash, redirect, url_for, request
from app.forms import LoginForm, RegistrationForm
from app.models import User
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit 
import sqlalchemy as sa


# controls what viewer will see (view functions!)
# two decorators creates association between url given as argument
# and the function (when web browser requests either of these two urls, Flask will invoke this function and pass return value to browser as response)
# HOME
@app.route('/')
@app.route('/index')
@login_required
def index():
    puzzles = [
        {
          'user': {'username': 'AgathaPuzzler'},
          'pieces': 1000,
          'title': 'Cocoa Beach' 
        },
        {
            'user': {'username': 'RavensburgerLover'},
            'pieces': 500,
            'title': 'Tranquility, ahhhh'
        }
    ]
    # rendertemplate() function included with Flask that uses Jinja template engine takes template filename
    # and returns html with placeholders replaced with values
    return render_template('index.html', title='Home', puzzles=puzzles)

# LOGIN
# will now accept get and post requests to server
@app.route('/login', methods=['GET', 'POST'])
def login():
    # if user already logged in, go to homepage
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    """
    will process the input of form based on what request is sent
    when GET requests sent to render form, validate_on_submit() will be False and therefore only show form
    when POST request sent upon pressing sign-in, it will return True, validation will occure
    if passes validation criteria, it will add data to server
    """
    if form.validate_on_submit():
        # gets list of users and gives you the one that matches the username
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        # if never signed in before or password hash does not match generated pwd hash (previously, if logged in before), show user msg
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            # shows login page again 
            return redirect(url_for('login'))
        # otherwise, log the user in and remember them
        # this will remember their unique id when visiting any pages while logged in
        login_user(user, remember=form.remember_me.data)
        # /login?next=/index
        # will give you part of url after ?
        # will return None if 'next' does not have a value after 
        has_value = request.args.get('next')
        # if has_value returns None OR if it's a relative url (ie no domain )
        if not has_value or urlsplit(has_value).netloc != '':
            # give value of 'next' in query string, the value of index
            has_value = url_for('index')
        # direct user to homepage
        return redirect(has_value)
    return render_template('login.html', title='Sign In', form=form)

# LOGOUT
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username = form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Success! Happy Puzzling!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

# PROFILE
# < > makes it populate dynamically based on who is logged in 
@app.route('/user/<username>')
@login_required
def user(username):
    # will get matching username from db and if no match will send 404 error to user (not found)
    user = db.first_or_404(sa.select(User).where(User.username == username))
    puzzles = [
        {
            'author': user,
            'pieces': 1000,
            'title': 'Puppies',
            'manufacturer': 'Ravensburger',
            'description': 'good condition' 
        },
        {
            'author': user,
            'pieces': 1000,
            'title': 'Kitties',
            'manufacturer': 'Puzzler',
            'description': 'excellent condition' 
        } 
    ]
    return render_template('user.html', user=user, puzzles=puzzles)