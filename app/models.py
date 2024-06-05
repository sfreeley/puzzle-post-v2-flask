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

# create User class
# db.Model is a base class for all models from Flask-SQLAlchemy 
class User(UserMixin, db.Model):
    # so.Mapped[type] defines the type of column ie (string, int, etc)
    # this also makes the values required in data base (so cannot be null)
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    # cannot have more than one username or email; index helps make retrieving individual rows
    # easier (acts like identifier)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), unique=True, index=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), unique=True, index=True)
    # in this case, Optional allow column to be nullable or empty
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))

    # connects to puzzle table (user can post many puzzles)
    # WriteOnlyMapped defines puzzles as collection type with Puzzle objects within it
    puzzles: so.WriteOnlyMapped['Puzzle'] = so.relationship(
        back_populates='author')

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


class Puzzle(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    # image:
    pieces: so.Mapped[int]
    title: so.Mapped[str] = so.mapped_column(sa.String(64))
    manufacturer: so.Mapped[str] = so.mapped_column(sa.String(64))
    description: so.Mapped[str] = so.mapped_column(sa.String(120))
    
    # lamba function -returns current time in UTC (standard for server side irregardless of location)
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    is_available: so.Mapped[bool]
    is_requested: so.Mapped[bool]
    in_progress: so.Mapped[bool]
    is_deleted: so.Mapped[bool]
    # foreign key (primary key on User table)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)

    # connects to User table
    author: so.Mapped[User] = so.relationship(back_populates='puzzles')

    def __repr__(self):
        return '<Puzzle {}>'.format(self.description)

# class UserPicture(db.Model, Image):
#     user_id: so.Mapped[int]

# function that will load a user based on their id
# flask-login will use this id for the user session so it knows who is logged in
@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))