from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)
