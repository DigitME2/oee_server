from flask import render_template

from app.documentation import bp


@bp.route('/help')
def help_home():
    """ Shows app instructions """
    return render_template('documentation/help.html')


@bp.route('/help/admin')
def admin():
    """ Shows app instructions """
    return render_template('documentation/admin.html')


@bp.route('/help/data')
def data():
    """ Shows app instructions """
    return render_template('documentation/data.html')


@bp.route('/help/android')
def android():
    """ Shows app instructions """
    return render_template('documentation/android.html')

