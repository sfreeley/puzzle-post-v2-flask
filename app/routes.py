from app import app, db
from flask import render_template, flash, redirect, url_for, request, send_from_directory, jsonify, session
from app.forms import LoginForm, RegistrationForm, EditProfileForm, CreatePuzzleForm, PersonalNote
from app.models import User, Puzzle, Category, Message
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit 
import sqlalchemy as sa
from sqlalchemy import or_, and_, func
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
    # try pagination
    page = request.args.get('page', 1, type=int)
    
    # only show puzzles that are not being requested
    # puzzles = db.session.query(Puzzle).filter_by(is_available=True).all()

    per_page = 2
    puzzles_pagination = db.session.query(Puzzle).filter_by(is_available=True).paginate(page=page, per_page=per_page, error_out=False)
    
    # rendertemplate() function included with Flask that uses Jinja template engine takes template filename
    # and returns html with placeholders replaced with values
    return render_template('index.html', title='Home', puzzles_pagination=puzzles_pagination)

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
    puzzles_current_user = db.session.query(Puzzle).filter_by(user_id=current_user.id, is_deleted=False).all()
    
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

# SOFT DELETE PUZZLE
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
            # 'delete' - change is_deleted to True and do not show on page through filtering
            puzzle_by_id.is_deleted == True
            puzzle_by_id.is_available == False
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

# SEND MESSAGE
@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    recipient_id = request.form['recipient_id']
    puzzle_id = request.form['puzzle_id']
    content = request.form['content']
    # get user that is the recipient of the message
    user = db.first_or_404(sa.select(User).where(User.id == recipient_id))
    if request.method == 'POST':
        # content = request.form.get('content')
        # if not content:
        #     flash('Message content cannot be empty.')
        #     return redirect(url_for('messages', user_id=user.id, puzzle_id=puzzle.id))
        # edit these fields to signify puzzle is being requested- should no longer show up on homepage
        # would need to edit the puzzle's is_requested value - change to true and change all other boolean values to false
        
        puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
        puzzle.is_available = False
        puzzle.is_requested = True
        db.session.commit()

        msg = Message(
            author=current_user,
            recipient=user,
            sender_requester_id=current_user.id, 
            recipient_owner_id=user.id,
            is_read = False,
            content=content, 
            puzzle_id=puzzle_id,
            timestamp=datetime.now(timezone.utc),
            is_deleted_by_sender=False,
            is_deleted_by_recipient=False,
            is_automated=False
        )
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent!')
        return redirect(url_for('messages', recipient_id=recipient_id, puzzle_id=puzzle_id ))
    return redirect(url_for('messages', recipient_id=recipient_id, puzzle_id=puzzle_id))

# show list of user conversations
# show conversations
# send messages using form
@app.route('/messages')
@login_required 
def messages():

    # whoever is getting the request for the puzzle 
    recipient_id = request.args.get('recipient_id')
    # id of puzzle requested
    puzzle_id = request.args.get('puzzle_id')
 

    # get all the users that have sent current_user messages (populate the list of users on page)
   
    # also want to show users that the current user has sent messages to but they have not replied back yet... 
    # need to get the count of unread messages sent from other users to the recipient (current_user)
    message_senders = db.session.query(
        User,
        User.id,
        
        # get count of messages where...
        # the current user has not read it and make sure the recipient is the current_user
        func.count(
                Message.id
        ).filter(
            and_(

                Message.is_read == False,
                Message.recipient_owner_id == current_user.id
            )
        ).label('unread_count')    
        # join the Message and User table to get all the users who sent or received messages
    ).join(
        Message,
        or_(
            Message.sender_requester_id == User.id,
            Message.recipient_owner_id == User.id
        )
    ).filter(
        # filter through the messages to get messages where the current user either sent or received messages 
        or_(
            Message.recipient_owner_id == current_user.id,
            Message.sender_requester_id == current_user.id
        )
    ).group_by(User.id).all()

    
    
    def get_most_recent_puzzle_id(sender_id, recipient_id):    
            most_recent_message = db.session.query(Message).filter(
                # get all correspondence between the users, whether they are senders or recipients 
                or_(
                    and_(Message.sender_requester_id == sender_id, Message.recipient_owner_id == recipient_id),
                    and_(Message.sender_requester_id == recipient_id, Message.recipient_owner_id == sender_id)
                ),
                Message.is_automated == False
            ).order_by(Message.timestamp.desc()).first()

            return most_recent_message.puzzle_id if most_recent_message else None
    
    senders_with_puzzle = []
    # sender = tuple
    for sender in message_senders:
        most_recent_puzzle_id = get_most_recent_puzzle_id(sender.id, current_user.id)
        # get actual sender object so can have access to all the functions in specific user object
        sender_object = User.query.get(sender.id)
        senders_with_puzzle.append({
            'sender': sender_object, 
            'most_recent_puzzle_id': most_recent_puzzle_id, 
            'unread_count': sender.unread_count
        })
    
    recipient = None
    messages_between_sender_recipient = []
    # check to see if there is a conversation between the two users 
    if recipient_id:
        recipient = User.query.get(recipient_id)
        messages_between_sender_recipient = db.session.query(Message).filter(
                ((Message.is_deleted_by_sender == False) & (Message.sender_requester_id == current_user.id)) | 
                ((Message.recipient_owner_id == current_user.id) & (Message.is_deleted_by_recipient == False)),

                ((Message.recipient_owner_id == current_user.id)) & ((Message.sender_requester_id == recipient.id)) |
                ((Message.recipient_owner_id == recipient.id)) & ((Message.sender_requester_id == current_user.id))
            ).order_by(Message.timestamp.asc()).all()
        
    # somehow need to find a way to get approve/decline to appear on last message of the related puzzle 
    # dictionary store last message Id 
    last_message_ids = {}

    for message in messages_between_sender_recipient:
        last_message_ids[message.puzzle_id] = message.id
    
    
    return render_template('messages.html', recipient=recipient, message_senders=senders_with_puzzle, conversation=messages_between_sender_recipient, puzzle_id=puzzle_id, last_message_ids=last_message_ids)

# mark individual messages as read
@app.route('/message/read/<int:message_id>', methods=['POST'])
@login_required
def mark_message_as_read(message_id):
    # get individual message by message_id
    message = db.session.query(Message).filter_by(id=message_id, recipient_owner_id=current_user.id).first()
    if message and not message.is_read:
        message.is_read = True
        db.session.commit()
        # will return JSON response (jsonify is function by Flask that converts Python dictionary to JSON response)
        # then stored as the response body
        # will be processed by the JS code in the messages.html page 
    # also need to somehow update user's unread message count...
    # use function from models? 
        unread_count = current_user.unread_message_count()
        return jsonify({'status': 'success', 'unread_count':unread_count})
    return jsonify({'status': 'failure'})


# SOFT DELETE MESSAGE
@app.route('/message/delete/<int:message_id>', methods=['GET', 'POST'])
@login_required
def delete_message(message_id):
    if request.method == 'POST':
        try:
            message = db.session.query(Message).filter_by(id=message_id).first()
        except Exception as e:
            flash("Something went wrong")
            return redirect(url_for('messages'))
        else:
            if message:
                # if the sender is the current_user...
                if message.sender_requester_id == current_user.id:
                    # change specific boolean to True so will only delete that current user's message, but not recipient
                    message.is_deleted_by_sender = True
                    db.session.commit()
                elif message.recipient_owner_id == current_user.id:
                    message.is_deleted_by_recipient = True
                    db.session.commit()    
                else:
                    flash("Something went wrong") 
                    return redirect(url_for('messages')) 
                flash("Your delete was successful")              
    return redirect(url_for('messages'))


# ACCEPT/DECLINE Request
@app.route('/request_action', methods=['GET', 'POST'])
@login_required
def request_action():  
    action = request.form.get('action')
    requester = request.form.get('requester')
    puzzle_id = request.form.get('puzzle_id')
    personal_note = request.form.get('personal_note')

    user = db.first_or_404(sa.select(User).where(User.username == requester))
    puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()

    form = PersonalNote()
    if not puzzle or not user:
        flash('Puzzle or user not found')
        return redirect(url_for('messages'))
    if request.method == 'POST':
        
        # personal_note = form.note.data
        if action == 'approve':
            
            # send pre-generated message to the requester of puzzle
            message_to_requester = f'Your request for puzzle, {puzzle.title}, has been approved! \n {personal_note}'
            puzzle.user_id = user.id
            puzzle.in_progress = True
            puzzle.is_available = False
            puzzle.is_requested = False
            db.session.commit()
        elif action == 'decline':
            
            message_to_requester = f'Your request for puzzle, {puzzle.title}, has been declined. \n {personal_note}'
            
            # puzzle user_id doesn't change
            # not in_progress
            puzzle.in_progress = False
            # goes back into circulation
            puzzle.is_available = True
            # not requested anymore
            puzzle.is_requested = False
            db.session.commit()
        else:
            flash('Invalid action')
            return redirect(url_for('messages'))
        
        msg = Message(
                author=current_user,
                recipient=user,
                content=message_to_requester,
                puzzle_id=puzzle_id,
                is_read=False,
                timestamp=datetime.now(timezone.utc),
                is_deleted_by_sender = False,
                is_deleted_by_recipient = False,
                is_automated=True
            )

        db.session.add(msg)
        db.session.commit()

        if action == 'approve':
            flash(f'You approved the puzzle request for {puzzle.title}. It now belongs to {puzzle.author.username}')
        else:
            flash(f'You declined the puzzle request from {user.username} for {puzzle.title}.')
        
    return redirect(url_for('messages'))
    # return render_template('messages.html', form=form)

# SEARCH
@app.route('/search', methods=['GET'])
def search():
    # try:
    # retrieve query parameter
    # request.args object that contains all query parameters sent with request
    # get('query', '') gets the value associated with the key named 'query'
    # if the value of query is not there, default to empty string
        query = request.args.get('query', '')
        page = request.args.get('page', 1, type=int)
        per_page = 2
        if query:
            results = Puzzle.query.join(Puzzle.categories).filter( 
                or_(
                Puzzle.title.ilike(f'%{query}%'),
                Puzzle.pieces.ilike(f'%{query}%'),
                Puzzle.manufacturer.ilike(f'%{query}%'),
                Puzzle.condition.ilike(f'%{query}%'),
                Puzzle.description.ilike(f'%{query}%'),
                Category.name.ilike(f'%{query}%')
            )
            ).paginate(page=page, per_page=per_page, error_out=False)
        else:
            results = Puzzle.query.paginate(page=page, per_page=per_page, error_out=False)
        return render_template('index.html', puzzles_pagination=results, query=query)
    #     results_data = [puzzle.to_dict() for puzzle in results]
    #     # results_data = [{'title': puzzle.title, 'pieces': puzzle.pieces, 'manufacturer': puzzle.manufacturer, 'condition': puzzle.condition, 'categories': puzzle.categories} for puzzle in results]
    #     return jsonify(results_data)
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500
    # iterate through results list and creates dictionary 
    
    # converts list of dictionaries, results_data, into JSON format for sending back as response to client
    # return jsonify(results_data)
      





