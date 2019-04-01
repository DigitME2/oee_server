from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo
from wtforms.widgets import TextArea


class ChangePasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Change')


class ActivityCodeForm(FlaskForm):
    code = StringField(validators=[DataRequired()])
    short_description = StringField(validators=[DataRequired()])
    long_description = StringField(widget=TextArea())
    graph_colour = StringField(validators=[DataRequired()])
    submit = SubmitField('Save')


    # id = db.Column(db.Integer, primary_key=True)
    # code = db.Column(db.String, unique=True)
    # short_description = db.Column(db.String)
    # long_description = db.Column(db.String)
    # graph_colour = db.Column(db.String)