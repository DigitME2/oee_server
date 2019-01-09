from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


"""Association table, storing which users are working on which groups of products"""
association_table = db.Table('users_batches',
                             db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                             db.Column('batch_id', db.Integer, db.ForeignKey('batch.id')))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    admin = db.Column(db.Boolean)

    recorded_data = db.relation('ProdData')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    #def __init__(self, username, admin):
    #    self.username = username
    #    self.admin = admin

    def __repr__(self):
        return '<User {}>'.format(self.username)


class Batch(db.Model):
    """Used to store batches of parts"""
    id = db.Column(db.Integer, primary_key=True)
    batch_number = db.Column(db.String, nullable=False)
    part_type_id = db.Column(db.Integer, db.ForeignKey('part_type.id'), nullable=False)

    users = db.relationship('User', secondary=association_table, lazy='dynamic', backref=db.backref('batches'))
    parts = db.relationship('Part')
    part_type = db.relationship('PartType', backref=db.backref('batches'))


class ProdData(db.Model):
    """ Holds the data recorded for each part/step during production"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    field_id = db.Column(db.Integer, db.ForeignKey('field.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    field_data = db.Column(db.String)


class Part(db.Model):
    """Used to store basic information about a single product"""
    id = db.Column(db.Integer, primary_key=True)
    start_timestamp = db.Column(db.Integer)
    relative_id = db.Column(db.Integer)  # The id to quickly identify the part within a batch, usually starting at 1
    batch_id = db.Column(db.Integer, db.ForeignKey('batch.id'))
    completed = db.Column(db.Boolean)
    completed_timestamp = db.Column(db.Integer)

    data = db.relationship('ProdData')


class Field(db.Model):
    """ Specifies which fields of data should appear for each step"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    step_id = db.Column(db.Integer, db.ForeignKey('step.id'))
    field_name = db.Column(db.String)
    batch_wide = db.Column(db.Boolean)  # True if the data field counts for all the parts in the batch

    data = db.relationship('ProdData')

    def clone_field(self, new_step_id):
        new_field = Field(step_id=new_step_id,
                          field_name=self.field_name,
                          batch_wide=self.batch_wide)
        db.session.add(new_field)
        db.session.commit()


class Step(db.Model):
    """Holds the information for each step for each type of part"""
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    part_type_id = db.Column(db.Integer, db.ForeignKey('part_type.id'))
    step_number = db.Column(db.Integer)
    step_title = db.Column(db.String)
    step_instructions = db.Column(db.String)
    step_image = db.Column(db.String)

    fields = db.relationship('Field')

    def clone_step(self, part_type_id):
        new_step = Step(part_type_id=part_type_id,
                        step_number=self.step_number,
                        step_title=self.step_title,
                        step_instructions=self.step_instructions,
                        step_image=self.step_image)
        db.session.add(new_step)
        db.session.commit()
        for field in self.fields:
            field.clone_field(new_step.id)



class PartType(db.Model):
    """Used to store different types of products"""
    id = db.Column(db.Integer, primary_key=True)
    part_name = db.Column(db.String)

    steps = db.relationship('Step')

    def clone_part_type(self):
        # Get next ID
        new_part_name = self.part_name + "(copy)"
        new_part_type = PartType(part_name= new_part_name)
        db.session.add(new_part_type)
        db.session.commit()
        for step in self.steps:
            step.clone_step(part_type_id=new_part_type.id)
        return new_part_type




class Order(db.Model):
    """Used to store an internal request for products to be made"""
    id = db.Column(db.Integer, primary_key=True)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


def copy_row(model, row, ignored_columns=[]):
    copy = model()

    for col in row.__table__.columns:
        if col.name not in ignored_columns:
            try:
                copy.__setattr__(col.name, getattr(row, col.name))
            except Exception as e:
                print(e)
                continue
    return copy