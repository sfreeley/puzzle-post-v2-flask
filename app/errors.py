from flask import render_template
from app import app, db

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    # if there is an internal error such as with the database, it will return it back to before the error if a transaction was taking place with the db
    db.session.rollback()
    return render_template('505.html'), 500