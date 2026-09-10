from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

HABIT_PALETTE = ["#e8ff6b", "#6bffd4", "#ff6b9d", "#6bb1ff", "#ffb06b", "#b06bff", "#6bffb0", "#ff8a6b"]


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    habits = db.relationship("Habit", backref="user", cascade="all, delete-orphan")
    tasks = db.relationship("Task", backref="user", cascade="all, delete-orphan")
    logs = db.relationship("Log", backref="user", cascade="all, delete-orphan")
    todos = db.relationship("ToDo", backref="user", cascade="all, delete-orphan")


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(120), default="")
    description = db.Column(db.Text, default="")
    color = db.Column(db.String(7), default="#e8ff6b")
    created_on = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    removed_on = db.Column(db.Date, nullable=True)

    tasks = db.relationship("Task", backref="habit", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name or "",
            "description": self.description or "",
            "color": self.color or "#e8ff6b",
            "created_on": self.created_on.isoformat() if self.created_on else "",
            "is_active": "1" if self.is_active else "0",
            "removed_on": self.removed_on.isoformat() if self.removed_on else "",
        }


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    habit_id = db.Column(db.Integer, db.ForeignKey("habit.id"), nullable=False)

    name = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    frequency = db.Column(db.Integer, default=1)
    unit = db.Column(db.String(10), default="day")
    created_on = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    removed_on = db.Column(db.Date, nullable=True)

    subtasks = db.relationship("Subtask", backref="task", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "habit_id": str(self.habit_id),
            "name": self.name or "",
            "description": self.description or "",
            "frequency": self.frequency or 1,
            "unit": self.unit or "day",
            "created_on": self.created_on.isoformat() if self.created_on else "",
            "is_active": "1" if self.is_active else "0",
            "removed_on": self.removed_on.isoformat() if self.removed_on else "",
        }


class Subtask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)

    name = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    frequency = db.Column(db.Integer, default=1)
    unit = db.Column(db.String(10), default="day")
    created_on = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    removed_on = db.Column(db.Date, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "task_id": str(self.task_id),
            "name": self.name or "",
            "description": self.description or "",
            "frequency": self.frequency or 1,
            "unit": self.unit or "day",
            "created_on": self.created_on.isoformat() if self.created_on else "",
            "is_active": "1" if self.is_active else "0",
            "removed_on": self.removed_on.isoformat() if self.removed_on else "",
        }


class ToDo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    name = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    deadline = db.Column(db.Date, nullable=True)
    created_on = db.Column(db.Date, nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    completed_on = db.Column(db.Date, nullable=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name or "",
            "description": self.description or "",
            "deadline": self.deadline.isoformat() if self.deadline else "",
            "created_on": self.created_on.isoformat() if self.created_on else "",
            "is_done": "1" if self.is_done else "0",
            "completed_on": self.completed_on.isoformat() if self.completed_on else "",
        }


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    date = db.Column(db.Date, nullable=False)
    task_id = db.Column(db.Integer, nullable=True)
    subtask_id = db.Column(db.Integer, nullable=True)
    occurrence = db.Column(db.Integer, nullable=False)
    done = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.Index(
            "uq_log_task_entry", "user_id", "date", "task_id", "occurrence",
            unique=True, postgresql_where=db.text("subtask_id IS NULL"),
        ),
        db.Index(
            "uq_log_subtask_entry", "user_id", "date", "subtask_id", "occurrence",
            unique=True, postgresql_where=db.text("task_id IS NULL"),
        ),
    )

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "task_id": str(self.task_id) if self.task_id else "",
            "subtask_id": str(self.subtask_id) if self.subtask_id else "",
            "occurrence": str(self.occurrence),
            "done": "1" if self.done else "0",
        }
