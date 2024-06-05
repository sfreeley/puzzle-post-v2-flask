import os
# for the FLASK-SQLAlchemy configuration
# absolute path of the directory of program
basedir = os.path.abspath(os.path.dirname(__file__))

# SECRET_KEY value generates signatures/tokens
# protects against cross-site request forgery
# value of secret key is set as two terms 
class Config:
    SECRET_KEY = os.environ.get('SECRET KEY') or 'cant-stop-wont-stop'
    """
        location of app's db taken from config var
        good practice to set config from env var and provide alternative
        when env does not define var
        if DATABASE_URL env var not defined, configure database called app.db 
        inside main dir of this application (basedir)
    """
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')