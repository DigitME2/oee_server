from app.extensions import db
from app.errors import bp
from flask import render_template


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@bp.errorhandler(404)
def file_not_found_error(error):
    return render_template('errors/404.html',
                           error=error), 404


@bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html',
                           error=error), 500


