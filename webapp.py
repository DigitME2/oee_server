from app import create_app

app = create_app()
app.db.create_all()
app.db.session.commit()
