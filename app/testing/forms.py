from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired

class NewBatchForm(FlaskForm):
    part_type = SelectField('Part Type')
    amount = IntegerField('Number of parts', validators=[DataRequired()])
    batch_number = StringField('Batch Number', validators=[DataRequired()])
    submit = SubmitField('Submit')

class TestForm(FlaskForm):
    testfield = SelectField('Test', choices=[1,2,3])
