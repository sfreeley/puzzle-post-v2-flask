from app import app, db
from flask import render_template, flash, redirect, url_for, request, send_from_directory, jsonify
from app.forms import LoginForm, RegistrationForm, CreatePuzzleForm
from app.models import User, Puzzle, Category, Message
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit 
import sqlalchemy as sa
from sqlalchemy import or_, and_, func
from datetime import datetime, timezone
from flask_wtf.file import FileRequired
from config import Config



# controls what viewer will see (view functions!)
# two decorators creates association between url given as argument
# and the function (when web browser requests either of these two urls, Flask will invoke this function and pass return value to browser as response)
# HOME
@app.route('/')
@app.route('/index')
@login_required
def index():
    # include search functionality -server side 
    query = request.args.get('query', '')
    # try pagination
    page = request.args.get('page', 1, type=int)
    per_page = 6
    if query:
        results = Puzzle.query.join(Puzzle.categories).filter( 
            or_(
            Puzzle.title.ilike(f'%{query}%'),
            Puzzle.pieces.ilike(f'%{query}%'),
            Puzzle.manufacturer.ilike(f'%{query}%'),
            Puzzle.condition.ilike(f'%{query}%'),
            Puzzle.description.ilike(f'%{query}%'),
            Category.name.ilike(f'%{query}%')
        ),
        Puzzle.user_id != current_user.id,
        Puzzle.is_deleted == False
    ).distinct().paginate(page=page, per_page=per_page, error_out=False)
    else:
        results = db.session.query(Puzzle).filter(Puzzle.is_available==True, Puzzle.user_id!=current_user.id).order_by(Puzzle.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    # rendertemplate() function included with Flask that uses Jinja template engine takes template filename
    # and returns html with placeholders replaced with values
    return render_template('index.html', title='Home', puzzles_pagination=results, query=query, user=user, show_buttons=False, small_card_size=True)

# SEARCH
# @app.route('/search', methods=['GET'])
# def search():
#     # try:
#     # retrieve query parameter
#     # request.args object that contains all query parameters sent with request
#     # get('query', '') gets the value associated with the key named 'query'
#     # if the value of query is not there, default to empty string
#         query = request.args.get('query', '')
#         page = request.args.get('page', 1, type=int)
#         per_page = 2
#         if query:
#             results = Puzzle.query.join(Puzzle.categories).filter( 
#                 or_(
#                 Puzzle.title.ilike(f'%{query}%'),
#                 Puzzle.pieces.ilike(f'%{query}%'),
#                 Puzzle.manufacturer.ilike(f'%{query}%'),
#                 Puzzle.condition.ilike(f'%{query}%'),
#                 Puzzle.description.ilike(f'%{query}%'),
#                 Category.name.ilike(f'%{query}%')
#             )
#             ).paginate(page=page, per_page=per_page, error_out=False)
#         else:
#             results = Puzzle.query.paginate(page=page, per_page=per_page, error_out=False)
#         return render_template('index.html', puzzles_pagination=results, query=query)
    #     results_data = [puzzle.to_dict() for puzzle in results]
    #     # results_data = [{'title': puzzle.title, 'pieces': puzzle.pieces, 'manufacturer': puzzle.manufacturer, 'condition': puzzle.condition, 'categories': puzzle.categories} for puzzle in results]
    #     return jsonify(results_data)
    # except Exception as e:
    #     return jsonify({'error': str(e)}), 500
    # iterate through results list and creates dictionary 
    
    # converts list of dictionaries, results_data, into JSON format for sending back as response to client
    # return jsonify(results_data)

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
    
    available_puzzles = []
    in_progress_puzzles = []
    requested_puzzles = []

    for puzzle in puzzles_current_user:
        if puzzle.is_available:
            sharing_count += 1
            available_puzzles.append(puzzle)
        elif puzzle.in_progress:
            progress_count += 1 
            in_progress_puzzles.append(puzzle)   
        elif puzzle.is_requested:
            requested_count += 1
            requested_puzzles.append(puzzle)
    return render_template('user.html', puzzles=puzzles_current_user, available_puzzles=available_puzzles, in_progress_puzzles=in_progress_puzzles, requested_puzzles=requested_puzzles, user=user, sharing_count=sharing_count, progress_count=progress_count, requested_count=requested_count, show_buttons=True)

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
    # form = EditProfileForm()
    # if POST-ing, save the new info into database
    if request.method == 'POST':
        username = request.form.get('username') 
        about_me = request.form.get('about_me')

    # make sure to check that user is not changing their current username to another already in db
   
        if username != current_user.username:
            user = User.query.filter_by(username=username).first()
            # return True or False
            if user:
                 flash('Username already taken')
                 return redirect(url_for('user', username=current_user.username))
       
        current_user.username = username
        current_user.about_me = about_me
        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('user', username=current_user.username))
        # return redirect(url_for('user', username=current_user.username))
               

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

    categories = db.session.query(Category).order_by(Category.name.asc()).all()
    form.categories.choices = [(category.id, category.name) for category in categories]

    conditions = ['Excellent', 'Good', 'Fair']
    # first condition- value of the condition 
    # second condition- label for radio button
    form.condition.choices = [(condition, condition) for condition in conditions]
  
    
    # if puzzle id is there from the form with hiddenfield..
    if puzzle_id:
        form.image.validators = [v for v in form.image.validators if not isinstance(v, FileRequired)]
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
    else:
               
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
@app.route('/puzzle/delete', methods=['GET', 'POST'])
@login_required
def delete_puzzle():
    # delete_type = request.form.get('delete-type')
    item_id = request.form.get('item_id') 
    # get the entry from db
    try:
        puzzle_by_id = db.session.query(Puzzle).filter_by(id=item_id).first()
    except Exception as e:
        flash("Something went wrong")
        return redirect(url_for('user', username=current_user.username))
    else:
        if puzzle_by_id and puzzle_by_id.user_id == current_user.id:
            # 'delete' - change is_deleted to True and do not show on page through filtering
            puzzle_by_id.is_deleted = True
            puzzle_by_id.is_available = False
            db.session.commit()
            flash("Your delete was successful. The puzzle is no longer in circulation.")
    return redirect(url_for('user', username=current_user.username))

# CONFIRM DELETE    
@app.route('/confirm_delete', methods=['GET'])
@login_required


def confirm_delete():
    delete_type = request.form.get('delete-type')
    item_id = request.form.get('item-id')

    if delete_type == 'puzzle':
        item = db.session.query(Puzzle).filter_by(id=item_id).first()
    elif delete_type == 'message':
        item = db.session.query(Message).filter_by(id=item_id).first()
    else:
        flash('Not valid delete type')
        return redirect(url_for('user', username=current_user.username))
    # return render_template('confirm_delete.html', delete_type=delete_type, item=item)

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
        if current_user.id != puzzle.user_id and not puzzle.in_progress:
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

@app.route('/request_puzzle/<int:puzzle_id>', methods=['GET', 'POST'])
@login_required
def request_puzzle(puzzle_id):
    puzzle = Puzzle.query.get_or_404(puzzle_id)
    puzzle.is_requested = True
    db.session.commit()
    return redirect(url_for('messages', recipient_id=puzzle.author.id, puzzle_id = puzzle_id))

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
    
    
    is_puzzle_in_progress = False
    is_puzzle_requested = False
    puzzle = Puzzle.query.get(puzzle_id)
    if puzzle:
        if puzzle.in_progress:
            is_puzzle_in_progress = True
        elif puzzle.is_requested:
            is_puzzle_requested = True
        
   
 

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

    def get_puzzles(sender_id, recipient_id):
        # query puzzles and join with messages table to get puzzles that matches what puzzle_id the message is referring to
        puzzles = db.session.query(Puzzle).join(
            Message,
            Puzzle.id == Message.puzzle_id
        # filter sender id of message is sender id and recipient is the recipient id OR sender is the recipient id and recipient is sender id  
        ).filter(
            or_(
                and_(Message.sender_requester_id == sender_id, Message.recipient_owner_id == recipient_id),
                and_(Message.sender_requester_id == recipient_id, Message.recipient_owner_id == sender_id)
            ),
        # filter out all the puzzles where the recipient or sender if the current user and the messages have been deleted by the current user 
            or_(
                and_(Message.recipient_owner_id == current_user.id, Message.is_deleted_by_recipient == False),
                and_(Message.sender_requester_id == current_user.id, Message.is_deleted_by_sender == False)
            )  
            # ensures only unique puzzle ids are returned    
        ).group_by(Puzzle.id).all()
        return puzzles

    
    senders_with_puzzle = []
    # sender = tuple
    for sender in message_senders:
        # returns list of puzzle objects- pass in sender id and current_user id is the recipient id
        puzzles = get_puzzles(sender.id, current_user.id)
        
        # get actual sender(user) object so can have access to all the functions in specific user object
        sender_object = User.query.get(sender.id)
        senders_with_puzzle.append({
            'sender': sender_object, 
            'puzzles': puzzles, 
            'unread_count': sender.unread_count
        })
    
    recipient = None
    messages_between_sender_recipient = []
    # check to see if there is a conversation between the two users 
    if recipient_id:
        recipient = User.query.get(recipient_id)
        messages_between_sender_recipient = db.session.query(Message).filter(

                and_(
                ((Message.is_deleted_by_sender == False) & (Message.sender_requester_id == current_user.id)) |
                ((Message.recipient_owner_id == current_user.id) & (Message.is_deleted_by_recipient == False)),

                ((Message.recipient_owner_id == current_user.id)) & ((Message.sender_requester_id == recipient.id)) |
                ((Message.recipient_owner_id == recipient.id)) & ((Message.sender_requester_id == current_user.id)),
                
                (Message.puzzle_id == puzzle_id)
            )
            ).order_by(Message.timestamp.asc()).all()
        
    # somehow need to find a way to get approve/decline to appear on last message of the related puzzle 
    # dictionary store last message Id 
    last_message_ids = {}

    for message in messages_between_sender_recipient:
        last_message_ids[message.puzzle_id] = message.id
    
    
    return render_template('messages.html', recipient=recipient, is_puzzle_in_progress=is_puzzle_in_progress, is_puzzle_requested=is_puzzle_requested, message_senders=senders_with_puzzle, conversation=messages_between_sender_recipient, puzzle_id=puzzle_id, last_message_ids=last_message_ids)


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
        
        unread_counts_by_sender = current_user.unread_message_counts_by_sender()
        return jsonify({'status': 'success', 'unread_count':unread_count, 'unread_counts': unread_counts_by_sender})
    return jsonify({'status': 'failure'})


# ----> SOFT DELETE MESSAGE
@app.route('/message/delete', methods=['GET', 'POST'])
@login_required
def delete_message():
    item_id = request.form.get('message_id')
    # recipient_id = request.form.get('recipient_id')
    # puzzle_id = request.form.get('puzzle_id_delete')

    if request.method == 'POST':
        try:
            message = db.session.query(Message).filter_by(id=item_id).first()
        except Exception as e:
            flash("Something went wrong")

            return redirect(url_for('messages'))
        else:
            if message:
                # if the sender is the current_user...
                if message.sender_requester_id == current_user.id:
                    # then recipient will be recipient_owner
                    recipient_id = message.recipient_owner_id
                    # change specific boolean to True so will only delete that current user's message, but not recipient
                    message.is_deleted_by_sender = True
                    db.session.commit()
                    # if message recipient is the current user...
                elif message.recipient_owner_id == current_user.id:
                    # recipient will be the sender of the message
                    recipient_id = message.sender_requester_id
                    message.is_deleted_by_recipient = True
                    db.session.commit()    
                else:
                    flash("Something went wrong") 
                    return redirect(url_for('messages'))
                flash("Your message was successfully deleted")              
    return redirect(url_for('messages', recipient_id=recipient_id, puzzle_id=message.puzzle_id))

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

    if not puzzle or not user:
        flash('Puzzle or user not found')
        return redirect(url_for('messages'))
    if request.method == 'POST':
        
        
        if action == 'approve':
            
            # send pre-generated message to the requester of puzzle
            message_to_requester = f'Your request for puzzle, {puzzle.title}, has been approved! -- {personal_note}'
            puzzle.user_id = user.id
            puzzle.in_progress = True
            puzzle.is_available = False
            puzzle.is_requested = False
            db.session.commit()
            
        elif action == 'decline':
            
            message_to_requester = f'Your request for puzzle, {puzzle.title}, has been declined. -- {personal_note}'
            
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
    

@app.route('/delete/message_thread', methods=['GET','POST'])
@login_required
def delete_message_thread():
    recipient_id = request.form.get('recipient_id')
    # id of puzzle requested
    puzzle_id = request.form.get('puzzle_id_delete')
    # query for specific puzzle id's messages between the two users
    messages_between_sender_recipient = []
    # check to see if there is a conversation between the two users 
    if recipient_id:
        recipient = User.query.get(recipient_id)
        messages_between_sender_recipient = db.session.query(Message).filter(

                and_(
                ((Message.is_deleted_by_sender == False) & (Message.sender_requester_id == current_user.id)) |
                ((Message.recipient_owner_id == current_user.id) & (Message.is_deleted_by_recipient == False)),

                ((Message.recipient_owner_id == current_user.id)) & ((Message.sender_requester_id == recipient.id)) |
                ((Message.recipient_owner_id == recipient.id)) & ((Message.sender_requester_id == current_user.id)),
                
                (Message.puzzle_id == puzzle_id)
            )
            ).all()
    if not messages_between_sender_recipient:
        flash("No messages found.")
        return redirect(url_for('messages'))
    # loop through and mark each message's message.is_deleted_by_recipient=True
    for message in messages_between_sender_recipient:
       if message.sender_requester_id == current_user.id:
           message.is_deleted_by_sender = True
       if message.recipient_owner_id == current_user.id:
           message.is_deleted_by_recipient = True
    db.session.commit()
    flash('Message thread successfully deleted.')   
    return redirect(url_for('messages'))

@app.route('/completed', methods=['POST'])
@login_required
def complete_puzzle():
    puzzle_id = request.form.get('puzzle_id')
    puzzle = db.session.query(Puzzle).filter_by(id=puzzle_id).first()
    puzzle.is_available = True
    puzzle.in_progress = False 
    db.session.commit()
    return redirect(url_for('user', username=current_user.username))



      





