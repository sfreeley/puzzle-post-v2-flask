from app import app, db
from flask import render_template, flash, redirect, url_for, request, send_from_directory
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CreatePuzzleForm, MessageForm
from app.models import User, Puzzle, Category, Message
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit 
import sqlalchemy as sa
from datetime import datetime, timezone
from flask_wtf.file import FileRequired
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
    # only show puzzles that are not being requested
    puzzles = db.session.query(Puzzle).filter_by(is_available=True).all()

    
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
    requested_count = 0
    progress_count = 0
    puzzles_current_user = db.session.query(Puzzle).filter_by(user_id=current_user.id).all()
    
    for puzzle in puzzles_current_user:
        if puzzle.is_available == True:
            sharing_count = sharing_count + 1
        elif puzzle.in_progress == True:
            progress_count = progress_count + 1    
        elif puzzle.is_requested == True:
            requested_count = requested_count + 1
    return render_template('user.html', puzzles=puzzles_current_user, user=user, sharing_count=sharing_count, progress_count=progress_count, requested_count=requested_count)

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

# edit
@app.route('/save_puzzle/<int:puzzle_id>', methods=['GET','POST'])
# create
@app.route('/save_puzzle', methods=['GET', 'POST'])
@login_required

# default puzzle_id is None
def save_puzzle(puzzle_id=None):
    form = CreatePuzzleForm()

    categories = Category.query.all()
    form.categories.choices = [(category.id, category.name) for category in categories]

    conditions = ['Excellent', 'Good', 'Fair']
    # first condition- value of the condition 
    # second condition- label for radio button
    form.condition.choices = [(condition, condition) for condition in conditions]
  
    
    # if puzzle id is there from the form with hiddenfield..
    if puzzle_id:
        # get puzzle from db by that puzzle_id and belongs to the user logged in
        puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id, user_id=current_user.id).first()
        if puzzle:
            # pre-populate fields with corresponding info from db
            if request.method == 'GET':
                form.puzzle_id.data = puzzle.id
                form.existing_image_url.data = puzzle.image_url
                form.title.data = puzzle.title
                form.pieces.data = puzzle.pieces
                form.condition.data = puzzle.condition
                form.manufacturer.data = puzzle.manufacturer
                form.description.data = puzzle.description
                form.categories.data = [category.id for category in puzzle.categories]
            # POST-ing as edit
            if form.validate_on_submit():
                if not form.categories.data:
                    form.categories.errors.append('Please select at leasat one category')
                    return render_template('create_puzzle.html', title='Save Puzzle', form=form)
                puzzle.title = form.title.data
                puzzle.pieces = form.pieces.data
                puzzle.condition = form.condition.data
                puzzle.manufacturer = form.manufacturer.data
                puzzle.description = form.description.data
                if form.categories.data == None:
                    form.categories.errors.append('Please select at leasat one category')
                    return redirect(url_for('/save_puzzle', puzzle_id=form.puzzle_id.data))
                # get all the categories based on id of specific input from user and loop through 
                puzzle.categories = [Category.query.get(category_id) for category_id in form.categories.data]
                if form.image.data:
                    uploaded_image = form.image.data
                    saved_image = Config.photos.save(uploaded_image)
                    file_url = url_for('get_file', filename=saved_image)
                    puzzle.image_url = file_url
                else:
                    puzzle.image_url = form.existing_image_url.data

                db.session.commit()
                return redirect(url_for('user', username=current_user.username)) 
    # creating puzzle 
    if puzzle_id is None:
        form.image.validators.append(FileRequired())        
        if form.validate_on_submit():
            puzzle = Puzzle(
                user_id = current_user.id,
                timestamp = datetime.now(timezone.utc),
                is_available = True,
                in_progress = False,
                is_requested = False,
                is_deleted = False
            )
            # if no exisiting puzzle, user input will be saved
            puzzle.title = form.title.data
            puzzle.pieces = form.pieces.data
            puzzle.condition = form.condition.data
            puzzle.manufacturer = form.manufacturer.data
            puzzle.description = form.description.data
            if not form.categories.data:
                    form.categories.errors.append('Please select at leasat one category')
                    return render_template('create_puzzle.html', title='Save Puzzle', form=form)
            # get all the categories based on id of specific input from user and loop through 
            puzzle.categories = [Category.query.get(category_id) for category_id in form.categories.data]

            if form.image.data:
                uploaded_image = form.image.data
                saved_image = Config.photos.save(uploaded_image)
                file_url = url_for('get_file', filename=saved_image)
                puzzle.image_url = file_url
            
            db.session.add(puzzle)
            db.session.commit()
            return redirect(url_for('user', username=current_user.username))
     
    return render_template('create_puzzle.html', title='Save Puzzle', form=form, choices=form.condition.choices, existing_image_url = form.existing_image_url.data)

# DELETE PUZZLE
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
@app.route('/confirm_delete/<delete_type>/<int:item_id>', methods=['GET'])
@login_required

# ***confirm delete pop-up (bootstrap?)
def confirm_delete(delete_type, item_id):
    if delete_type == 'puzzle':
        item = db.session.query(Puzzle).filter_by(id=item_id).first()
    elif delete_type == 'message':
        item = db.session.query(Message).filter_by(id=item_id).first()
    else:
        flash('Not valid delete type')
        return redirect(url_for('user', username=current_user.username))
    return render_template('confirm_delete.html', delete_type=delete_type, item=item)

# DELETE MESSAGE
@app.route('/message/delete/<int:message_id>', methods=['GET', 'DELETE'])
@login_required
def delete_message(message_id):
    try:
        message = db.session.query(Message).filter_by(id=message_id).first()
    except Exception as e:
        flash("Something went wrong")
        return redirect(url_for('user', username=current_user.username))
    else:
        if message and message.recipient.id == current_user.id:
            db.session.delete(message)
            db.session.commit()
            return redirect(url_for('messages'))

# SEND MESSAGE
@app.route('/send_message/<recipient>/<int:puzzle_id>', methods=['GET', 'POST'])
@login_required
def send_message(recipient, puzzle_id):
    user = db.first_or_404(sa.select(User).where(User.username == recipient))
    puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
    # would need to edit the puzzle's is_requested value - change to true and change all other boolean values to false
    if not puzzle:
        flash('Puzzle not found.')
        return redirect(url_for('user', username=current_user.username))
    
    # edit these fields to signify puzzle is being requested- should no longer show up on homepage
    puzzle.is_available = False
    puzzle.is_requested = True
    db.session.commit()

    form = MessageForm(puzzle_id=puzzle_id, recipient=recipient)
    if form.validate_on_submit():
        msg = Message(
            author=current_user, 
            recipient=user, 
            content=form.message.data, 
            puzzle_id=form.puzzle_id.data,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent!')
        return redirect(url_for('user', username=current_user.username))
    
    return render_template('send_message.html', title='Send Message', form=form, recipient=recipient, puzzle=puzzle)

# SHOW LIST OF MESSAGES/LIST OF USERS who have sent current user messages
@app.route('/messages')
@app.route('/messages/from/<int:user_id>')
@login_required
def messages(user_id=None):
    # will update the last message read time to current time 
    # will mark everything as read 
    current_user.last_message_read_time = datetime.now(timezone.utc)
    db.session.commit()
    # get the current_user
    recipient = db.session.query(User).filter_by(username=current_user.username).first()
    # get all the users that have sent current_user messages (populate the list of users on page)
    # user table join messages on message.author.id=user.id and find the messages where the recipient is the current_user (get distinct because don't want repeat of users)
    message_senders = db.session.query(User).join(Message, Message.sender_requester_id == User.id).where(Message.recipient_owner_id == current_user.id).distinct().all()

    selected_user = None
    messages_between_sender_recipient = []

    if user_id:
        # get the user that sent the message
        selected_user = db.session.query(User).get(user_id)
        if selected_user:
            # all messages by sender to recipient using user_id passed by url through clicking username
            messages_between_sender_recipient = db.session.query(Message).where(
                ((Message.recipient_owner_id == current_user.id) & (Message.sender_requester_id == user_id)) |
                ((Message.recipient_owner_id == user_id) & (Message.sender_requester_id == current_user.id))
            ).order_by(Message.timestamp.desc()).all()
    return render_template('messages.html', message_senders=message_senders, selected_user=selected_user, recipient=recipient, messages=messages_between_sender_recipient )

# ACCEPT/DECLINE Request
@app.route('/request_action/<action>/<requester>/<int:puzzle_id>', methods=['GET', 'POST'])
@login_required
def request_action(action, requester, puzzle_id):
    user = db.first_or_404(sa.select(User).where(User.username == requester))
    puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
    
    if not puzzle or not user:
        flash('Puzzle or user not found')
        return redirect(url_for('messages'))
    if action == 'approve':
        # send pre-generated message to the requester of puzzle
        message_to_requester = f'Your request for puzzle, {puzzle.title}, has been approved!'
        puzzle.user_id = user.id
        puzzle.in_progress = True
        puzzle.is_available = False
        puzzle.is_requested = False
    elif action == 'decline':
        message_to_requester = f'Your request for puzzle, {puzzle.title}, has been declined. If needed, reach out to the owner for more information.'
        
        # puzzle user_id doesn't change
        # not in_progress
        puzzle.in_progress = False
        # goes back into circulation
        puzzle.is_available = True
        # not requested anymore
        puzzle.is_requested = False
    else:
        flash('Invalid action')
        return redirect(url_for('messages'))
    
    msg = Message(
            author=current_user,
            recipient=user,
            content=message_to_requester,
            puzzle_id=puzzle_id,
            timestamp=datetime.now(timezone.utc)
        )

    db.session.add(msg)
    db.session.commit()

    if action == 'approve':
        flash(f'You approved the puzzle request for {puzzle.title}. It now belongs to {puzzle.author.username}')
    else:
        flash(f'You declined the puzzle request from {puzzle.author.username} for {puzzle.title}.')
        
    return redirect(url_for('messages'))

