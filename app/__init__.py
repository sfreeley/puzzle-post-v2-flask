from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_uploads import configure_uploads


"""
-Flask wrapper for Alembic, the migration framework for SQLAlchemy
-will allow changes without having to recreate db everytime change made
-Alembic maintains a migration repository storing migration scripts, which means
when changes made, a new script added to repository that documents change
-scripts are executed in same order they were created 
"""
from flask_migrate import Migrate
# create application object as instance of class Flask
# __name__ predefined var set to name of module in which it's used
app = Flask(__name__)

# login
login = LoginManager(app)
login.login_view = 'login'

# read the config file and apply it 
app.config.from_object(Config)

# db object
db = SQLAlchemy(app)

# db migration object
migrate = Migrate(app, db)

# handle images
configure_uploads(app, Config.photos)

# routes will handle diff views when user requests url 
from app import routes, models, errors