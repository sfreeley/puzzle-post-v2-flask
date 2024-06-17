from app import app, db
from flask import render_template, flash, redirect, url_for, request, send_from_directory
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CreatePuzzleForm
from app.models import User, Puzzle, Category
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit 
import sqlalchemy as sa
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
# import os
# import cloudinary
# from cloudinary import uploader
from werkzeug.utils import secure_filename
from config import Config


# controls what viewer will see (view functions!)
# two decorators creates association between url given as argument
# and the function (when web browser requests either of these two urls, Flask will invoke this function and pass return value to browser as response)
# HOME
@app.route('/')
@app.route('/index')
@login_required
def index(): 
    puzzles = db.session.query(Puzzle).all()

    
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
    sharing_count = 0
    progress_count = 0
    puzzles_current_user = db.session.query(Puzzle).filter_by(user_id=current_user.id).all()
    
    for puzzle in puzzles_current_user:
        if puzzle.is_available == True:
            sharing_count = sharing_count + 1
            # return sharing_count
        elif puzzle.in_progress == True:
            progress_count = progress_count + 1
            # return in_progress
    return render_template('user.html', puzzles=puzzles_current_user, user=user, sharing_count=sharing_count, progress_count=progress_count)

# executed before any of the view functions are executed
# checks if the current user is logged in and lets you set last seen as that time 
@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

#EDIT PROFILE
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    # if POST-ing, save the new info into database
    if form.validate_on_submit():
        if not form.check_username_available(form.username.data):
            current_user.username = form.username.data
            current_user.about_me = form.about_me.data
            db.session.commit()
            return redirect(url_for('user', username=current_user.username))
        else:
            flash("Username already taken")
            return redirect(url_for('edit_profile'))
    # if GET-ing and user wants to edit the profile, show the current info first 
    # (what's already in the db)
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile', form=form, user=user)



# get image url 
@app.route('/uploads/<filename>')
def get_file(filename):
    return send_from_directory(Config.UPLOADED_PHOTOS_DEST, filename)

# CREATE PUZZLE
@app.route('/create_puzzle', methods=['GET', 'POST'])
@login_required
def create_puzzle():
    form = CreatePuzzleForm()
  
    categories = Category.query.all()
    form.categories.choices = [(category.id, category.name) for category in categories]
    
    # conditions
    conditions = ['Excellent', 'Good', 'Fair']
    form.condition.choices = [(condition, condition) for condition in conditions]
    if form.puzzle_id.data:
        edit_puzzle(form.puzzle_id.data)
        
    if form.validate_on_submit():  
        uploaded_image = form.image.data     
        saved_image = Config.photos.save(uploaded_image)
        file_url = url_for(get_file, filename=saved_image)
        new_puzzle = Puzzle(
            title = form.title.data,
            image_url = file_url,
            pieces = form.pieces.data,
            condition = form.condition.data,
            manufacturer = form.manufacturer.data,
            description = form.description.data,
            timestamp = datetime.now(timezone.utc),
            user_id = current_user.id,
            is_available = True,
            in_progress = False,
            is_requested = False,
            is_deleted = False
        )
        # get category IDs from what user selects from form 
        for category_id in form.categories.data:
            category = Category.query.get(category_id)
            new_puzzle.categories.append(category) 
        db.session.add(new_puzzle)
        db.session.commit()
        return redirect(url_for('user', username=current_user.username))
    return render_template('create_puzzle.html', title='Create Puzzle', form=form, choices=form.condition.choices, cat_choices=form.categories.choices)

# EDIT Puzzle
@app.route('/edit_puzzle/<int:puzzle_id>', methods=['GET', 'POST'])
@login_required
def edit_puzzle(puzzle_id):
    form = CreatePuzzleForm()
    categories = Category.query.all()
    form.categories.choices = [(category.id, category.name) for category in categories]
    
    # conditions
    conditions = ['Excellent', 'Good', 'Fair']
    form.condition.choices = [(condition, condition) for condition in conditions]
    
    puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
    selected_category_ids = [category.id for category in puzzle.categories]
    
    form.title.data = puzzle.title.strip()
    form.image.data = puzzle.image_url
    form.pieces.data = puzzle.pieces
    form.condition.data = puzzle.condition
    form.manufacturer.data = puzzle.manufacturer
    form.description.data = puzzle.description   
    form.categories.data = selected_category_ids

    if form.validate_on_submit():  
        uploaded_image = form.image.data     
        saved_image = Config.photos.save(uploaded_image)
        file_url = url_for(get_file, filename=saved_image)
        edit_puzzle = Puzzle(
            title = form.title.data,
            image_url = file_url,
            pieces = form.pieces.data,
            condition = form.condition.data,
            manufacturer = form.manufacturer.data,
            description = form.description.data,
            timestamp = datetime.now(timezone.utc),
            user_id = current_user.id,
            is_available = True,
            in_progress = False,
            is_requested = False,
            is_deleted = False
        )
        # get category IDs from what user selects from form 
        for category_id in form.categories.data:
            category = Category.query.get(category_id)
            edit_puzzle.categories.append(category) 
        db.session.add(edit_puzzle)
        db.session.commit()
        return redirect(url_for('user', username=current_user.username))
    return render_template('create_puzzle.html', title='Edit Puzzle', form=form, choices=form.condition.choices)



# DELETE
@app.route('/puzzle/delete/<int:puzzle_id>', methods=['GET', 'DELETE'])
@login_required
def delete_puzzle(puzzle_id):
      
    # get the entry from db
    try:
        puzzle_by_id = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
    except Exception as e:
        flash("Something went wrong")
        return redirect(url_for('user', username=current_user.username))
    else:
        if puzzle_by_id and puzzle_by_id.user_id == current_user.id:
            # delete from db
            db.session.delete(puzzle_by_id)
            db.session.commit()
            return redirect(url_for('user', username=current_user.username))

# CONFIRM DELETE    
@app.route('/puzzle/confirm_delete/<int:puzzle_id>', methods=['GET'])
# ***confirm delete pop-up (bootstrap?)
def confirm_delete(puzzle_id):
    puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
    return render_template('confirm_delete.html', puzzle=puzzle)