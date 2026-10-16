from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user
from app.models import Test

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Public home/landing page of the examination portal."""
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))
        
    active_exams_count = Test.query.filter_by(is_published=True).count()
    return render_template('index.html', active_exams_count=active_exams_count)


@main_bp.route('/about')
def about():
    """Information regarding the project objectives, architecture, and technology stack."""
    return render_template('about.html')
