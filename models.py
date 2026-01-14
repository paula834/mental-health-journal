from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.Integer, nullable=False)

    emotion = db.Column(db.String(50))
    energy = db.Column(db.Integer)
    sleep = db.Column(db.Integer)

    # Physical sensations
    jaw_tension = db.Column(db.Integer)
    shoulder_tension = db.Column(db.Integer)
    stomach_discomfort = db.Column(db.Integer)
    headache = db.Column(db.Integer)

    # Thought log
    trigger_event = db.Column(db.Text)
    negative_thought = db.Column(db.Text)
    reframed_thought = db.Column(db.Text)

    # Gratitude & affirmation
    gratitude_1 = db.Column(db.String(255))
    gratitude_2 = db.Column(db.String(255))
    gratitude_3 = db.Column(db.String(255))
    affirmation = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    media = db.relationship(
        'EntryMedia',
        backref='entry',
        cascade='all, delete-orphan',
        lazy=True
    )


class WeeklyReflection(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    boundary_check = db.Column(db.Text)
    weekly_goal = db.Column(db.Text)

    week_start = db.Column(db.Date, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class EntryMedia(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    entry_id = db.Column(
        db.Integer,
        db.ForeignKey('entry.id'),
        nullable=False
    )

    file_path = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)  # image | audio | video
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
