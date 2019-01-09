from app import db
from app.errors import bp
from flask import render_template


@bp.errorhandler(404)
def file_not_found_error(error):
    return render_template('errors/404.html'), 404


@bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500