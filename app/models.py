from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User model representing registered candidates (students) and exam administrators (faculty).
    Table: users (id, full_name, email, password_hash, role, created_at)
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    attempts = db.relationship('Attempt', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash password securely using established PBKDF2/scrypt through Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify candidate password against securely stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Test(db.Model):
    """
    Test model representing an academic examination.
    Table: tests (id, title, description, duration_minutes, total_marks, is_published, created_at)
    """
    __tablename__ = 'tests'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    total_marks = db.Column(db.Integer, nullable=False, default=100)
    passing_percentage = db.Column(db.Float, nullable=True)  # Optional pass threshold (None if unconfigured)
    is_published = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    questions = db.relationship('Question', backref='test', lazy=True, cascade='all, delete-orphan')
    attempts = db.relationship('Attempt', backref='test', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Test {self.id}: {self.title}>'


class Question(db.Model):
    """
    Question model representing an objective MCQ test item.
    Table: questions (id, test_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks)
    """
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    marks = db.Column(db.Integer, nullable=False, default=1)

    # Relationships
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')

    def to_student_dict(self):
        """
        Sanitized representation for students that NEVER exposes correct_option
        preventing answer leaks via template inspection or network inspection.
        """
        return {
            'id': self.id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'marks': self.marks
        }

    def __repr__(self):
        return f'<Question {self.id} for Test {self.test_id}>'


class Attempt(db.Model):
    """
    Attempt model representing a candidate's sitting for a test.
    Table: attempts (id, user_id, test_id, started_at, submitted_at, score, status)
    """
    __tablename__ = 'attempts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, default=0.0, nullable=False)
    status = db.Column(db.String(20), default='In Progress', nullable=False)  # 'In Progress', 'Completed'

    # Relationships
    answers = db.relationship('Answer', backref='attempt', lazy=True, cascade='all, delete-orphan')

    @property
    def maximum_marks(self):
        """Total possible marks configured for the test."""
        if self.test and self.test.total_marks > 0:
            return float(self.test.total_marks)
        if self.test and self.test.questions:
            return float(sum(q.marks for q in self.test.questions))
        return 0.0

    @property
    def percentage(self):
        """Calculated score percentage."""
        max_m = self.maximum_marks
        if max_m > 0:
            return round((self.score / max_m) * 100, 2)
        return 0.0

    @property
    def has_passing_threshold(self):
        """Check if an administrator-configured passing percentage threshold exists."""
        return bool(self.test and self.test.passing_percentage is not None)

    @property
    def is_passed(self):
        """Evaluates whether attempt passed, strictly if a configured threshold exists; otherwise None."""
        if self.has_passing_threshold:
            return self.percentage >= self.test.passing_percentage
        return None

    @property
    def correct_count(self):
        """Count of correctly answered questions."""
        return sum(1 for a in self.answers if a.is_correct)

    @property
    def incorrect_count(self):
        """Count of answered questions that were incorrect."""
        return sum(1 for a in self.answers if a.selected_option and not a.is_correct)

    @property
    def unanswered_count(self):
        """Count of unanswered questions."""
        total_q = len(self.test.questions) if self.test else len(self.answers)
        answered_q = sum(1 for a in self.answers if a.selected_option)
        return max(0, total_q - answered_q)

    @property
    def total_questions_count(self):
        """Total questions count for this examination."""
        if self.test and self.test.questions:
            return len(self.test.questions)
        return len(self.answers)

    @property
    def time_taken_seconds(self):
        """Total elapsed seconds from start to submission."""
        if self.submitted_at and self.started_at:
            delta = int((self.submitted_at - self.started_at).total_seconds())
            return max(0, delta)
        return None

    @property
    def formatted_time_taken(self):
        """Human-readable time taken (e.g., '12m 45s' or '35s')."""
        secs = self.time_taken_seconds
        if secs is None:
            return "N/A"
        mins = secs // 60
        rem_secs = secs % 60
        if mins > 0:
            return f"{mins}m {rem_secs}s"
        return f"{rem_secs}s"

    @property
    def remaining_seconds(self):
        """Calculate accurate server-enforced countdown remaining seconds."""
        if self.status != 'In Progress':
            return 0
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        total_time = (self.test.duration_minutes * 60) if self.test else 1800
        return max(0, int(total_time - elapsed))

    def is_expired(self, grace_seconds=30):
        """Check if examination time deadline has passed on the server."""
        if self.status != 'In Progress':
            return True
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        total_time = (self.test.duration_minutes * 60) if self.test else 1800
        return elapsed > (total_time + grace_seconds)

    def __repr__(self):
        return f'<Attempt {self.id} User:{self.user_id} Test:{self.test_id} Score:{self.score}>'


class Answer(db.Model):
    """
    Answer model representing an examinee's chosen response for a question.
    Table: answers (id, attempt_id, question_id, selected_option, is_correct, marks_awarded)
    """
    __tablename__ = 'answers'

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey('attempts.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=True)  # 'A', 'B', 'C', 'D' or None
    is_correct = db.Column(db.Boolean, default=False, nullable=False)
    marks_awarded = db.Column(db.Float, default=0.0, nullable=False)
    is_marked_for_review = db.Column(db.Boolean, default=False, nullable=False)

    def __repr__(self):
        return f'<Answer {self.id} Attempt:{self.attempt_id} Q:{self.question_id} Opt:{self.selected_option}>'

