from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship("Task", backref="user", cascade="all, delete-orphan")
    logs = db.relationship("Log", backref="user", cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    type = db.Column(db.String(120), default="")
    name = db.Column(db.String(255), default="")
    subtask = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    frequency = db.Column(db.Integer, default=1)
    parent_id = db.Column(db.Integer, nullable=True)
    created_on = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    removed_on = db.Column(db.Date, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "type": self.type or "",
            "name": self.name or "",
            "subtask": self.subtask or "",
            "description": self.description or "",
            "frequency": self.frequency or 1,
            "parent_id": str(self.parent_id) if self.parent_id else "",
            "created_on": self.created_on.isoformat() if self.created_on else "",
            "is_active": "1" if self.is_active else "0",
            "removed_on": self.removed_on.isoformat() if self.removed_on else "",
        }


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    task_id = db.Column(db.Integer, nullable=False)
    occurrence = db.Column(db.Integer, nullable=False)
    done = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", "task_id", "occurrence", name="uq_log_entry"),
    )

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "task_id": str(self.task_id),
            "occurrence": str(self.occurrence),
            "done": "1" if self.done else "0",
        }
