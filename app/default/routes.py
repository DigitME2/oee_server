from app.default import bp
from app.default.models import setup_database
from flask import render_template, redirect, url_for
from flask_login import current_user, login_required


@bp.route('/')
def default():
    # Fill the database with default values
    setup_database()
    return redirect(url_for('login.login'))


@bp.route('/index')
@login_required
def index():
    """ The default page """
    if current_user.is_authenticated:
        user = {'username': current_user.username, 'id': current_user.id}
    else:
        user = {'username': "nobody"}
    return render_template('default/index.html', title='Index', user=user)


