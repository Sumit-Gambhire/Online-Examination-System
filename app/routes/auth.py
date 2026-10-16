import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle student candidate authentication."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('identifier', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        # Server-side validation
        if not email or not password:
            flash('Both college email and password are required.', 'danger')
            return render_template('auth/login.html')

        if not EMAIL_REGEX.match(email):
            flash('Please provide a valid email format (e.g. student@college.edu).', 'warning')
            return render_template('auth/login.html')

        # Parameterized query via SQLAlchemy
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password credentials. Please verify and try again.', 'danger')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.full_name}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        if user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Dedicated login route for faculty administrators."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))

    # Check if any administrator currently exists in the database
    has_admin = User.query.filter_by(role='admin').first() is not None

    if request.method == 'POST':
        email = request.form.get('identifier', '').strip().lower()
        password = request.form.get('password', '')
        remember = True if request.form.get('remember') else False

        if not email or not password:
            flash('Please enter your administrator email and password.', 'danger')
            return render_template('auth/admin_login.html', has_admin=has_admin)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid administrator credentials.', 'danger')
            return render_template('auth/admin_login.html', has_admin=has_admin)

        if not user.is_admin:
            flash('Access restricted. This account does not possess administrator privileges.', 'warning')
            return render_template('auth/admin_login.html', has_admin=has_admin)

        login_user(user, remember=remember)
        flash(f'Welcome back, Faculty Admin {user.full_name}!', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('auth/admin_login.html', has_admin=has_admin)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Allow new student candidates to register an examination profile."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Server-Side Form Data Validation
        errors = []

        if not full_name or len(full_name) < 2:
            errors.append('Full name must be at least 2 characters long.')

        if not email or not EMAIL_REGEX.match(email):
            errors.append('Please provide a valid email address.')

        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('auth/register.html')

        # Prevent duplicate registration using the same email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('This email address is already registered. Please log in instead.', 'warning')
            return render_template('auth/register.html')

        # Create new student user securely
        new_user = User(
            full_name=full_name,
            email=email,
            role='student'  # Candidate registration is always strictly scoped to 'student'
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Registration completed successfully! You can now log in with your email.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Terminate the current user session."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))
