from app import app, db
import sqlalchemy as sa
import sqlalchemy.orm as so
from app.models import User, Puzzle

# configuring a flask shell (python interpreter) within the application
# so it can recognize everything within your app and 
# will be easier to use when manipulating and testing the db (without having to import each time) 
@app.shell_context_processor
def make_shell_context():
    return {
        'sa': sa,
        'so': so,
        'db': db,
        'User': User,
        'Puzzle': Puzzle
    }