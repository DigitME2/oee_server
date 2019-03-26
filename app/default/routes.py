from flask import render_template, redirect, url_for
from flask_login import current_user, login_required
from app.default.models import Machine, Job
from app.login.models import User

# test code
from app import db
from app.oee_monitoring import bp


@bp.route('/')
def default():
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


@bp.route('/adminhome', methods=['GET'])
@login_required
def admin_home():
    """ The default page for a logged-in user"""
    return render_template('default/adminhome.html',
                           machines=Machine.query.all(),
                           users=User.query.all(),
                           jobs=Job.query.all())
