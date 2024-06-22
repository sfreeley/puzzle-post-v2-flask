# Python typing hint
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
# from sqlalchemy_imageattach.entity import Image, image_attachment
from datetime import datetime, timezone
# packages included in flask Werkzeug involved in password hashing for login
from werkzeug.security import generate_password_hash, check_password_hash
# flask-login (UserMixin contains these properties and methods-)
# is_authenticated, is_active, is_anonymous, get_id()
from flask_login import UserMixin
from app import db, login
from hashlib import md5


# create User class
# db.Model is a base class for all models from Flask-SQLAlchemy 
class User(UserMixin, db.Model):
    # so.Mapped[type] defines the type of column ie (string, int, etc)
    # this also makes the values required in data base (so cannot be null)
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    # cannot have more than one username or email; index helps make retrieving individual rows
    # easier (acts like identifier)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, index=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), unique=True, index=True)
    # in this case, Optional allow column to be nullable or empty
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    # messages implementation
    last_message_read_time: so.Mapped[Optional[datetime]]
    messages_sent: so.WriteOnlyMapped['Message'] = so.relationship(
        foreign_keys='Message.sender_requester_id', back_populates='author'
    )

    messages_received: so.WriteOnlyMapped['Message'] = so.relationship(
        foreign_keys='Message.recipient_owner_id', back_populates='recipient'
    )

    # connects to puzzle table (user can post many puzzles)
    # WriteOnlyMapped defines puzzles as collection type with Puzzle objects within it
    puzzles: so.WriteOnlyMapped['Puzzle'] = so.relationship(
        back_populates='author')
    
    def unread_message_count(self):
        # last_message_read_time will have last time user visited messages page
        # if it's none, then it will assign last_read_time to it, otherwise if None then assign 1990-01-01 (handles missing or undefined values) 
        last_read_time = self.last_message_read_time or datetime(1990, 1, 1)

        # count the number of rows (ie messages)
        count_query = sa.select(sa.func.count()).where(Message.recipient == self, Message.timestamp > last_read_time)
        # execute and return the count query and get one result with scalar()
        return db.session.scalar(count_query)
    # this built in function of objects returns printable representation of the object
    # generally used to make debugging easier
    def __repr__(self):
        return '<User {}>'.format(self.username)

    # generates hash based on user input (password)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # checks to see if user's inputted password matches password hash created
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # creating avatars for users
    def create_avatar(self, size):
        digest = md5(self.username.lower().encode('utf-8)')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

# ***association table b/w puzzle and category
puzzle_category = sa.Table(
    'puzzle_category',
    db.metadata,
    sa.Column('puzzle_id', sa.Integer, sa.ForeignKey('puzzle.id'), primary_key=True),
    sa.Column('category_id', sa.Integer, sa.ForeignKey('category.id'), primary_key=True)
)

class Category(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(64), nullable=False)

    # many to many relationship with puzzles (forward reference puzzle)
    puzzles = so.relationship('Puzzle', secondary=puzzle_category,
        back_populates='categories')
    
    def __repr__(self):
        return '<Category {}>'.format(self.name)


class Puzzle(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    image_url: so.Mapped[str] = so.mapped_column(nullable=False)
    pieces: so.Mapped[int]
    condition: so.Mapped[str] = so.mapped_column(sa.String(64), nullable=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(64))
    manufacturer: so.Mapped[str] = so.mapped_column(sa.String(64))
    description: so.Mapped[Optional[str]] = so.mapped_column(sa.String(120))
    # returns current time in UTC (standard for server side irregardless of location)
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    is_available: so.Mapped[bool]
    is_requested: so.Mapped[bool]
    in_progress: so.Mapped[bool]
    is_deleted: so.Mapped[bool]
    # foreign key (primary key on User table)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)

    # connects to User table
    author: so.Mapped[User] = so.relationship(back_populates='puzzles')
 
    # back_populates-links puzzles in Category with categories relationship in Puzzle (bidirectional)
    categories = so.relationship(Category, secondary=puzzle_category, back_populates='puzzles')

    # messages = so.Mapped['Message'] = so.relationship(back_populates='puzzle') 
    def __repr__(self):
        return '<Puzzle {}>'.format(self.description)

# Message
class Message(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    puzzle_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(Puzzle.id), index=True)
    sender_requester_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    recipient_owner_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    content: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(
        index=True, default=lambda: datetime.now(timezone.utc))
    is_deleted: so.Mapped[bool]
    
    # user relationships
    author: so.Mapped[User] = so.relationship(
        foreign_keys="Message.sender_requester_id",
        back_populates='messages_sent'

    )
    recipient: so.Mapped[User] = so.relationship(
        foreign_keys="Message.recipient_owner_id",
        back_populates="messages_received"
    )

    # puzzle relationship
    
    puzzle = so.relationship(Puzzle, backref='messages')
    
    def __repr__(self):
        return '<Message{}>'.format(self.content)

# function that will load a user based on their id (stores user's session)
# flask-login will use this id for the user session so it knows who is logged in
@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))