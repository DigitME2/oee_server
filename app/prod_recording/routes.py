from app import db
from app.prod_recording import bp
from app.prod_recording.forms import NewPartTypeForm, NewBatchForm
from app.prod_recording.models import Batch, Part, Step, Field, PartType, ProdData
from flask import render_template, request, flash, redirect, url_for, abort
from flask_login import current_user, login_required
import os


@login_required
@bp.route('/home')
def home():
    """ The default page for a logged-in user

    This will show the user the batches they are currently working on, as well as the option to start a new batch
    """
    batches = current_user.batches
    admin = current_user.admin
    nav_bar_title = "Home - " + current_user.username
    return render_template('prod_recording/home.html',
                           nav_bar_title=nav_bar_title,
                           batches=batches,
                           admin=admin)


@login_required
@bp.route('/batch')
def batch():
    """ The page showing a batch's information."""
    try:
        batch_id = request.args.get("batch_id")
        current_batch = Batch.query.filter_by(id=batch_id).first()
    except TypeError:
        flash("Bad batch selected")
        return redirect(url_for('home'))
    return render_template('prod_recording/batch.html', batch=current_batch)


@bp.context_processor
def field_processor():
    def get_field_data(part_id, field_id):
        pd = ProdData.query.filter_by(part_id=part_id, field_id=field_id).first()
        if pd is not None:
            return pd.field_data
        else:
            return ""

    return dict(get_field_data=get_field_data)


@login_required
@bp.route('/production', methods=['GET', 'POST'])
def production():
    """ The page that shows up during production, showing instructions and prompting for data that needs recording."""
    try:
        current_batch = Batch.query.get_or_404(request.args.get("batch_id"))
        steps = Step.query.filter_by(part_type_id=current_batch.part_type_id).all()

    except TypeError:
        flash("Bad step or batch selected")
        return redirect(url_for('home'))
    nav_bar_title = str(current_batch.part_type.part_name) + " - Batch " + str(current_batch.batch_number)

    if request.method == 'POST':
        # Save the data
        try:
            # Get the current step being saved
            step = Step.query.get_or_404(request.form['stepId'])
            # Loop through each part
            for part in current_batch.parts:
                # For each field in the step, save the data in the database
                for field in step.fields:
                    # Try and retrieve the old entry if one already exists
                    pd = ProdData.query.filter_by(part_id=part.id, field_id=field.id).first()
                    # Create it if it doesn't exist
                    if pd is None:
                        pd = ProdData(part_id=part.id, field_id=field.id, user_id=current_user.id)

                    # Check whether checkbox is checked and therefore all parts should share the same value
                    all_parts_checkbox_name = "checkboxId" + str(field.id)
                    if all_parts_checkbox_name in request.form:
                        # Use the value from the all-parts field
                        all_parts_field_name = "0:" + str(field.id)
                        pd.field_data = request.form[all_parts_field_name]
                    else:
                        # Each html element is named "part_id:field_id"
                        html_field_name = str(part.id) + ":" + str(field.id)
                        pd.field_data = request.form[html_field_name]
                    # Assign the current user to the edit
                    pd.user_id = current_user.id
                    db.session.add(pd)
                    db.session.commit()
            scroll_to = "step" + str(step.id)
            return render_template('prod_recording/production.html',
                                   nav_bar_title=nav_bar_title,
                                   current_batch=current_batch,
                                   steps=steps,
                                   scroll_to=scroll_to)

        except:
            flash("Bad request")


    return render_template('prod_recording/production.html',
                           nav_bar_title=nav_bar_title,
                           current_batch=current_batch,
                           steps=steps)


@bp.route('/newbatch', methods=['GET', 'POST'])
def new_batch():
    """The page to create a new batch"""
    form = NewBatchForm()
    # Create list of part names to fill the part-type selection box
    part_names = []
    for p in PartType.query.all():
        part_names.append((str(p.id), p.part_name))
    form.part_type.choices = part_names

    # Create a new batch, and new parts when form is submitted
    if form.validate_on_submit():
        batch = Batch(batch_number=form.batch_number.data, part_type_id=form.part_type.data, users=[current_user])
        db.session.add(batch)
        db.session.commit()  # Need to commit here so that the batch is assigned an id
        for i in range(0, form.amount.data):
            part = Part(batch_id=batch.id, relative_id=i + 1)
            db.session.add(part)
            # When a new part is created, create all the blank prodData entries for every field in every step
            for step in batch.part_type.steps:
                for field in step.fields:
                    pd = ProdData(part_id=part.id, field_id=field.id, field_data="")
                    db.session.add(pd)
        db.session.commit()
        return redirect(url_for('home'))
    nav_bar_title = "Create new batch"
    return render_template('prod_recording/newbatch.html', form=form,
                           nav_bar_title=nav_bar_title)




@login_required
@bp.route('/adminbatch', methods=['GET', 'POST'])
def admin_batch():
    """The page to see current batches for admins"""
    try:
        current_batch = Batch.query.get_or_404(request.args.get("batch_id"))
    except TypeError:
        flash("Bad step or batch selected")
        return redirect(url_for('home'))

    part_type = PartType.query.get_or_404(current_batch.part_type_id)

    return render_template('prod_recording/adminbatch.html', batch=current_batch, part_type=part_type)


# @login_required
@bp.route('/createparttype', methods=['GET', 'POST'])
def create_part_type():
    """The page to create a part type"""

    form = NewPartTypeForm()
    part_type_id = request.args.get("part_type_id")
    part_type = PartType.query.filter_by(id=part_type_id).first()
    # Create a list of steps for the part
    steps = Step.query.filter_by(part_type_id=part_type_id).all()
    steps.sort(key=lambda step: step.step_number)

    if form.validate_on_submit():
        part_type.part_name = form.part_name.data
        db.session.commit()

    # Fill in the part name form to the current part name
    form.part_name.data = part_type.part_name

    return render_template('prod_recording/createparttype.html',
                           part_type=part_type,
                           steps=steps,
                           form=form)


@bp.route('/newparttype', methods=['POST'])
def new_part_type():
    part_type = PartType(part_name="New Part")
    db.session.add(part_type)
    db.session.commit()
    return redirect(url_for('create_part_type', part_type_id=part_type.id))


# @login_required
@bp.route('/editstep', methods=['GET', 'POST'])
def edit_step():
    """The page to edit a step for a part"""

    try:
        part_type_id = request.args.get("part_type_id")
        step_id = request.args.get("step_id")
    except:
        abort(400)
        return
    # Send the user back if the part is uneditable
    if step_id is None or part_type_id is None:
        abort(400)
        return

    part_type = PartType.query.get_or_404(part_type_id)

    # Save step info
    if Batch.query.filter_by(part_type_id=part_type_id).first() is not None:
        flash("Parts already exist for this part type, and it can no longer be edited.")
        return redirect(request.referrer)
    step = Step.query.get_or_404(step_id)
    fields = Field.query.filter_by(step_id=step_id).all()
    # Form is an image upload
    if request.method == 'POST':
        # Save the step info
        step.step_title = request.form['stepTitle']
        step.step_instructions = request.form['stepInstructions']

        # Upload the image
        if 'image' in request.files:
            image = request.files['image']
            # Check the image has the correct file extension
            fn, file_extension = os.path.splitext(image.filename)
            if file_extension not in app.config['ALLOWED_EXTENSIONS']:
                flash("Incorrect file extension")
                return redirect(request.referrer)
            # Create the directory if it doesn't exist
            directory = '/'.join([app.config['UPLOAD_FOLDER'], part_type.part_name])
            if not os.path.exists(directory):
                os.mkdir(directory)
            filename = "step" + str(step.step_number) + file_extension
            # Delete the image if one already exists
            if os.path.isfile('/'.join([directory, filename])):
                try:
                    os.remove('/'.join([directory, filename]))
                except OSError:
                    pass
            # Save the image
            image.save('/'.join([directory, filename]))
            # Save the location of the image to the database for retrieval
            step.step_image = '/'.join(["/static/images", part_type.part_name, filename])

        db.session.commit()

    nav_bar_title = str(part_type.part_name) + " - " + "Step " + str(step.step_number)
    return render_template('prod_recording/step.html',
                           nav_bar_title=nav_bar_title,
                           part_type=part_type,
                           step=step,
                           fields=fields)


@bp.route('/addstep', methods=['POST'])
def add_step():
    """Adds a new step for a part"""

    part_type_id = request.form["part_type_id"]

    # Check that a batch hasn't been created with this part type
    if Batch.query.filter_by(part_type_id=part_type_id).first() is not None:
        flash("Parts already exist for this part type, and it can no longer be edited.")
        return redirect(request.referrer)

    steps = Step.query.filter_by(part_type_id=part_type_id).all()

    # Find the next step number
    # = 1 if there are no steps
    if len(steps) == 0:
        new_step_number = 1
    else:
        new_step_number = max(s.step_number for s in steps) + 1
    # Create the default Step title
    step_title = "Step " + str(new_step_number)
    step_instructions = ""
    step = Step(part_type_id=part_type_id,
                step_number=new_step_number,
                step_title=step_title,
                step_instructions=step_instructions)
    db.session.add(step)
    db.session.commit()
    return redirect(request.referrer)


@bp.route('/deletestep', methods=['POST'])
def delete_step():
    part_type_id = request.form["part_type_id"]
    steps = Step.query.filter_by(part_type_id=part_type_id).all()
    # Check that a batch hasn't been created with this part type
    if Batch.query.filter_by(part_type_id=part_type_id).first() is not None:
        flash("Parts already exist for this part type, and it can no longer be edited.")
        return redirect(request.referrer)

    if len(steps) == 0:
        return redirect(request.referrer)
    else:
        # Delete the final step
        steps.sort(key=lambda step: step.step_number)
        last_step = steps[-1]
        db.session.delete(last_step)
        db.session.commit()
        return redirect(request.referrer)


@bp.route('/savedatafield', methods=['POST'])
def save_field():
    """ The POST request to add a data field when editing a step"""
    field_name = request.json.get("field_name")
    step_id = request.json.get("step_id")
    batch_wide = request.json.get("batch_wide")
    f = Field(field_name=field_name, step_id=step_id, batch_wide=batch_wide)
    db.session.add(f)
    db.session.commit()
    return '', 201


@bp.route('/deletedatafield', methods=['POST'])
def delete_field():
    """ The POST request to delete a data field during creation of a step"""
    field_name = request.json.get("field_name")
    step_id = request.json.get("step_id")
    field = Field.query.filter_by(field_name=field_name, step_id=step_id).first()
    db.session.delete(field)
    db.session.commit()
    return '', 201



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['UPLOAD_FOLDER']


@app.context_processor
def utility_functions():
    def print_in_console(message):
        print(str(message))

    return dict(mdebug=print_in_console)