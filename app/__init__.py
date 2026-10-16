import os
import secrets
import click
from flask import Flask, session, request, abort
from flask_login import LoginManager
from app.config import Config
from app.models import db, User, Test, Question, Attempt, Answer

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def seed_sample_curriculum(app):
    """Seed sample academic test with objective questions if no test exists yet."""
    with app.app_context():
        # Check if sample test exists
        existing_test = Test.query.first()
        if not existing_test:
            sample_test = Test(
                title='Computer Science & Web Development Fundamentals',
                description='Comprehensive multiple-choice assessment evaluating Core Python, Web Architectures, Database Design, and Network Protocols.',
                duration_minutes=20,
                total_marks=20,
                is_published=True
            )
            db.session.add(sample_test)
            db.session.flush()

            # Objective questions matching the required schema:
            # (test_id, question_text, option_a, option_b, option_c, option_d, correct_option, marks)
            sample_questions = [
                {
                    'question_text': 'Which of the following data structures in Python is immutable?',
                    'option_a': 'List',
                    'option_b': 'Tuple',
                    'option_c': 'Dictionary',
                    'option_d': 'Set',
                    'correct_option': 'B',
                    'marks': 5
                },
                {
                    'question_text': 'What does WSGI stand for in Python web architectures?',
                    'option_a': 'Web Server Gateway Interface',
                    'option_b': 'Wide System Gateway Integration',
                    'option_c': 'Web Standard General Interface',
                    'option_d': 'Web Socket Global Interface',
                    'correct_option': 'A',
                    'marks': 5
                },
                {
                    'question_text': 'Which relational constraint ensures that every email address in a users table is unique?',
                    'option_a': 'PRIMARY KEY',
                    'option_b': 'FOREIGN KEY',
                    'option_c': 'UNIQUE',
                    'option_d': 'CHECK',
                    'correct_option': 'C',
                    'marks': 5
                },
                {
                    'question_text': 'In Flask, which HTTP request method should be used when transmitting sensitive credentials?',
                    'option_a': 'GET',
                    'option_b': 'POST',
                    'option_c': 'PUT',
                    'option_d': 'DELETE',
                    'correct_option': 'B',
                    'marks': 5
                }
            ]

            for q in sample_questions:
                question_record = Question(
                    test_id=sample_test.id,
                    question_text=q['question_text'],
                    option_a=q['option_a'],
                    option_b=q['option_b'],
                    option_c=q['option_c'],
                    option_d=q['option_d'],
                    correct_option=q['correct_option'],
                    marks=q['marks']
                )
                db.session.add(question_record)

            db.session.commit()

        # Check for optional environment-variable-based admin provisioning
        env_admin_email = os.environ.get('ADMIN_EMAIL')
        env_admin_pass = os.environ.get('ADMIN_PASSWORD')
        if env_admin_email and env_admin_pass:
            if not User.query.filter_by(email=env_admin_email).first():
                admin_user = User(
                    full_name=os.environ.get('ADMIN_NAME', 'System Administrator'),
                    email=env_admin_email,
                    role='admin'
                )
                admin_user.set_password(env_admin_pass)
                db.session.add(admin_user)
                db.session.commit()


def register_cli_commands(app):
    """Register development CLI commands for secure administrator initialization."""
    @app.cli.command('create-admin')
    @click.option('--name', prompt='Administrator Full Name', help='Full Name of the faculty administrator')
    @click.option('--email', prompt='Administrator Email', help='Unique college email for the admin')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Secure password')
    def create_admin(name, email, password):
        """Secure CLI command to create the initial faculty administrator."""
        with app.app_context():
            normalized_email = email.strip().lower()
            existing_user = User.query.filter_by(email=normalized_email).first()
            if existing_user:
                click.echo(click.style(f"Error: A user with email '{normalized_email}' already exists.", fg='red'))
                return

            if len(password) < 6:
                click.echo(click.style("Error: Administrator password must be at least 6 characters.", fg='red'))
                return

            new_admin = User(
                full_name=name.strip(),
                email=normalized_email,
                role='admin'
            )
            new_admin.set_password(password)
            db.session.add(new_admin)
            db.session.commit()
            click.echo(click.style(f"Success! Faculty Administrator '{normalized_email}' created successfully.", fg='green'))

def setup_csrf_protection(app):
    """Zero-dependency, session-based CSRF protection for all state-changing forms."""
    def get_csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']

    app.jinja_env.globals['csrf_token'] = get_csrf_token

    @app.before_request
    def check_csrf():
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            if (app.testing or app.config.get('TESTING')) and not request.form.get('csrf_token'):
                return None
            token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
            expected = session.get('_csrf_token')
            if not expected or not token or not secrets.compare_digest(token, expected):
                abort(400, description="CSRF token validation failed. Please refresh and try again.")


def create_app(config_class=Config):
    """Application factory for the Online Examination System."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions & CSRF protection
    setup_csrf_protection(app)
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Register CLI management commands
    register_cli_commands(app)

    # Automatic database initialization & initial curriculum seeding
    with app.app_context():
        db.create_all()
        seed_sample_curriculum(app)

    return app
