from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired

class NewPartTypeForm(FlaskForm):
    part_name = StringField('Part Name', validators=[DataRequired()])
    submit = SubmitField('Save Name')


class NewBatchForm(FlaskForm):
    part_type = SelectField('Part Type')
    amount = IntegerField('Number of parts', validators=[DataRequired()])
    batch_number = StringField('Batch Number', validators=[DataRequired()])
    submit = SubmitField('Submit')
