from flask import render_template, url_for, redirect, request, abort, flash
from flask_login import login_required, current_user

from app import db
from app.admin import bp
from app.admin.helpers import admin_required
from app.admin.forms import ChangePasswordForm, ActivityCodeForm
from app.default.models import Machine, ActivityCode, Job, UNEXPLAINED_DOWNTIME_CODE_ID, UPTIME_CODE_ID
from app.login.models import User


@bp.route('/adminhome', methods=['GET'])
@login_required
@admin_required
def admin_home():
    """ The default page for a logged-in user"""
    return render_template('admin/adminhome.html',
                           machines=Machine.query.all(),
                           users=User.query.all(),
                           activity_codes=ActivityCode.query.all(),
                           jobs=Job.query.all())


@bp.route('/changepassword', methods=['GET', 'POST'])
@login_required
@admin_required
def change_password():
    """ The page to change a user's password. The user_id is passed to this page."""
    if current_user.admin is not True:
        abort(403)
    user = User.query.get_or_404(request.args.get('user_id'))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        redirect(url_for('admin.admin_home'))
    nav_bar_title = "Change password for " + str(user.username)
    return render_template("admin/changepassword.html", nav_bar_title=nav_bar_title, user=user, form=form)


@bp.route('/activitycode', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity_code():
    """The page to edit an activity code"""

    try:
        activity_code_id = int(request.args['ac_id'])
    except:
        return redirect(url_for('admin.admin_home'))

    if activity_code_id == UPTIME_CODE_ID:
        warning = "This code is automatically assigned when the machine is running"
    elif activity_code_id == UNEXPLAINED_DOWNTIME_CODE_ID:
        warning = "This code is the default downtime code assigned when the machine isn't running"
    else:
        warning = ""

    activity_code = ActivityCode.query.get_or_404(activity_code_id)
    form = ActivityCodeForm()
    if form.validate_on_submit():
        activity_code.code = form.code.data
        activity_code.short_description = form.short_description.data
        activity_code.long_description = form.long_description.data
        activity_code.graph_colour = '#' + form.graph_colour.data
        db.session.add(activity_code)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    form.code.data = activity_code.code
    form.short_description.data = activity_code.short_description
    form.long_description.data = activity_code.long_description
    form.graph_colour.data = activity_code.graph_colour

    return render_template("admin/activity_code.html",
                           form=form,
                           warning=warning)

