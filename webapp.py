from app import create_app, db

app = create_app()
db.create_all()
db.session.commit()
