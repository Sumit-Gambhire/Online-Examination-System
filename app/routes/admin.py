from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.models import db, User, Test, Question, Attempt, Answer

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
def check_admin_access():
    """
    Enforce strict role-based access control (RBAC).
    Prevent unauthenticated users and students from accessing any administrative functionality.
    """
    if request.endpoint == 'admin.login':
        return None

    if not current_user.is_authenticated:
        flash('Please authenticate with administrator credentials.', 'warning')
        return redirect(url_for('auth.admin_login'))

    if not current_user.is_admin:
        flash('Access restricted. Administrative privileges are required.', 'danger')
        return redirect(url_for('student.dashboard'))


@admin_bp.route('/login')
def login():
    """Direct redirection to administrative login."""
    return redirect(url_for('auth.admin_login'))


@admin_bp.route('/dashboard')
def dashboard():
    """
    Admin dashboard displaying:
    - Registered students count
    - Published tests count and total tests
    - Total completed test attempts
    - Recent student results with sensible pagination/limit
    """
    total_students = User.query.filter_by(role='student').count()
    total_exams = Test.query.count()
    published_exams = Test.query.filter_by(is_published=True).count()
    total_submissions = Attempt.query.filter_by(status='Completed').count()

    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Paginated attempts
    attempts_query = Attempt.query.filter_by(status='Completed').order_by(Attempt.submitted_at.desc())
    recent_attempts = attempts_query.limit(per_page).offset((page - 1) * per_page).all()
    total_pages = (total_submissions + per_page - 1) // per_page if total_submissions > 0 else 1

    all_tests = Test.query.order_by(Test.created_at.desc()).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_exams=total_exams,
        published_exams=published_exams,
        total_submissions=total_submissions,
        exams=all_tests,
        recent_results=recent_attempts,
        current_page=page,
        total_pages=total_pages
    )


@admin_bp.route('/exams', methods=['GET', 'POST'])
def exams():
    """List all examinations and handle new test creation."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        try:
            duration_minutes = int(request.form.get('duration_minutes', 30))
            total_marks = int(request.form.get('total_marks', 100))
            pass_pct_raw = request.form.get('passing_percentage', '').strip()
            passing_percentage = float(pass_pct_raw) if pass_pct_raw else None
            if passing_percentage is not None and (passing_percentage < 0 or passing_percentage > 100):
                flash('Passing benchmark percentage must be between 0 and 100.', 'warning')
                return redirect(url_for('admin.exams'))
        except (ValueError, TypeError):
            flash('Duration, marks, and passing threshold must be valid numbers.', 'danger')
            return redirect(url_for('admin.exams'))

        is_published = True if request.form.get('is_published') else False

        # Form Validation
        if not title:
            flash('Examination title is required.', 'danger')
            return redirect(url_for('admin.exams'))

        if len(title) > 150:
            flash('Examination title cannot exceed 150 characters.', 'danger')
            return redirect(url_for('admin.exams'))

        if duration_minutes < 1 or duration_minutes > 360:
            flash('Duration must be between 1 and 360 minutes.', 'danger')
            return redirect(url_for('admin.exams'))

        if total_marks < 1 or total_marks > 1000:
            flash('Total marks must be between 1 and 1000 points.', 'danger')
            return redirect(url_for('admin.exams'))

        new_test = Test(
            title=title,
            description=description,
            duration_minutes=duration_minutes,
            total_marks=total_marks,
            passing_percentage=passing_percentage,
            is_published=is_published
        )
        db.session.add(new_test)
        db.session.commit()

        flash(f'Examination "{title}" successfully created! Now author its questions below.', 'success')
        return redirect(url_for('admin.exam_questions', exam_id=new_test.id))

    all_tests = Test.query.order_by(Test.created_at.desc()).all()
    return render_template('admin/exams.html', exams=all_tests)


@admin_bp.route('/exam/<int:exam_id>/edit', methods=['GET', 'POST'])
def edit_exam(exam_id):
    """Edit existing examination details: title, description, duration, and marks."""
    test = db.session.get(Test, exam_id)
    if not test:
        abort(404)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()

        try:
            duration_minutes = int(request.form.get('duration_minutes', 30))
            total_marks = int(request.form.get('total_marks', 100))
            pass_pct_raw = request.form.get('passing_percentage', '').strip()
            passing_percentage = float(pass_pct_raw) if pass_pct_raw else None
            if passing_percentage is not None and (passing_percentage < 0 or passing_percentage > 100):
                flash('Passing benchmark percentage must be between 0 and 100.', 'warning')
                return render_template('admin/edit_exam.html', exam=test)
        except (ValueError, TypeError):
            flash('Duration, marks, and passing percentage must be valid numbers.', 'danger')
            return render_template('admin/edit_exam.html', exam=test)

        is_published = True if request.form.get('is_published') else False

        # Validation
        if not title:
            flash('Examination title cannot be empty.', 'danger')
            return render_template('admin/edit_exam.html', exam=test)

        if duration_minutes < 1 or duration_minutes > 360:
            flash('Duration must be between 1 and 360 minutes.', 'danger')
            return render_template('admin/edit_exam.html', exam=test)

        if total_marks < 1 or total_marks > 1000:
            flash('Total marks must be between 1 and 1000 points.', 'danger')
            return render_template('admin/edit_exam.html', exam=test)

        test.title = title
        test.description = description
        test.duration_minutes = duration_minutes
        test.total_marks = total_marks
        test.passing_percentage = passing_percentage
        test.is_published = is_published

        db.session.commit()
        flash(f'Examination "#{test.id}: {test.title}" updated successfully.', 'success')
        return redirect(url_for('admin.exams'))

    return render_template('admin/edit_exam.html', exam=test)


@admin_bp.route('/exam/<int:exam_id>/toggle', methods=['POST'])
def toggle_exam(exam_id):
    """Publish or unpublish an examination."""
    test = db.session.get(Test, exam_id)
    if not test:
        abort(404)

    test.is_published = not test.is_published
    db.session.commit()
    state = "Published" if test.is_published else "Unpublished (Draft)"
    flash(f'Test "{test.title}" status changed to: {state}.', 'info')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/exam/<int:exam_id>/delete', methods=['POST'])
def delete_exam(exam_id):
    """
    Delete an examination.
    SAFETY RULE:
    Prevents deleting a test if student attempt records exist, preventing orphaned/inconsistent grades.
    """
    test = db.session.get(Test, exam_id)
    if not test:
        abort(404)

    attempt_count = Attempt.query.filter_by(test_id=test.id).count()
    if attempt_count > 0:
        flash(
            f'Cannot delete examination "#{test.id}: {test.title}" because {attempt_count} student attempt(s) '
            f'exist on record. To preserve academic integrity, please unpublish the test instead to prevent new attempts.',
            'warning'
        )
        return redirect(url_for('admin.exams'))

    test_title = test.title
    db.session.delete(test)
    db.session.commit()
    flash(f'Examination "{test_title}" and its questions were safely deleted.', 'info')
    return redirect(url_for('admin.exams'))


@admin_bp.route('/questions')
def questions():
    """Question management entry point; redirects to active test."""
    all_tests = Test.query.order_by(Test.title).all()
    first_test = all_tests[0] if all_tests else None
    if first_test:
        return redirect(url_for('admin.exam_questions', exam_id=first_test.id))
    return render_template('admin/questions.html', exams=all_tests, current_exam=None, questions=[])


@admin_bp.route('/exam/<int:exam_id>/questions', methods=['GET', 'POST'])
def exam_questions(exam_id):
    """View and author MCQ questions for an examination."""
    current_test = db.session.get(Test, exam_id)
    if not current_test:
        abort(404)

    all_tests = Test.query.order_by(Test.title).all()

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_option = request.form.get('correct_option', '').strip().upper()

        try:
            marks = int(request.form.get('marks', 1))
        except (ValueError, TypeError):
            flash('Marks must be a valid integer.', 'danger')
            return redirect(url_for('admin.exam_questions', exam_id=current_test.id))

        # Strict MCQ Validation
        if not question_text:
            flash('Question text cannot be blank.', 'danger')
            return redirect(url_for('admin.exam_questions', exam_id=current_test.id))

        if not option_a or not option_b or not option_c or not option_d:
            flash('Each question must provide all 4 options (Option A, B, C, D).', 'danger')
            return redirect(url_for('admin.exam_questions', exam_id=current_test.id))

        if correct_option not in ['A', 'B', 'C', 'D']:
            flash('Exactly one correct option (A, B, C, or D) must be assigned.', 'danger')
            return redirect(url_for('admin.exam_questions', exam_id=current_test.id))

        if marks < 1 or marks > 50:
            flash('Question marks must be between 1 and 50 points.', 'danger')
            return redirect(url_for('admin.exam_questions', exam_id=current_test.id))

        new_question = Question(
            test_id=current_test.id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
            marks=marks
        )
        db.session.add(new_question)
        db.session.commit()

        flash('Question and 4 MCQ options successfully added to question bank!', 'success')
        return redirect(url_for('admin.exam_questions', exam_id=current_test.id))

    questions_list = Question.query.filter_by(test_id=current_test.id).order_by(Question.id.asc()).all()
    total_assigned_marks = sum(q.marks for q in questions_list)

    return render_template(
        'admin/questions.html',
        exams=all_tests,
        current_exam=current_test,
        questions=questions_list,
        total_assigned_marks=total_assigned_marks
    )


@admin_bp.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
def edit_question(question_id):
    """Edit existing question text, 4 options, correct answer key, and marks."""
    question = db.session.get(Question, question_id)
    if not question:
        abort(404)

    test = question.test

    if request.method == 'POST':
        question_text = request.form.get('question_text', '').strip()
        option_a = request.form.get('option_a', '').strip()
        option_b = request.form.get('option_b', '').strip()
        option_c = request.form.get('option_c', '').strip()
        option_d = request.form.get('option_d', '').strip()
        correct_option = request.form.get('correct_option', '').strip().upper()

        try:
            marks = int(request.form.get('marks', 1))
        except (ValueError, TypeError):
            flash('Marks must be a valid integer.', 'danger')
            return render_template('admin/edit_question.html', question=question, test=test)

        if not question_text or not option_a or not option_b or not option_c or not option_d:
            flash('Question text and all 4 options are required.', 'danger')
            return render_template('admin/edit_question.html', question=question, test=test)

        if correct_option not in ['A', 'B', 'C', 'D']:
            flash('Please choose exactly one correct option (A, B, C, or D).', 'danger')
            return render_template('admin/edit_question.html', question=question, test=test)

        if marks < 1 or marks > 50:
            flash('Marks must be between 1 and 50 points.', 'danger')
            return render_template('admin/edit_question.html', question=question, test=test)

        question.question_text = question_text
        question.option_a = option_a
        question.option_b = option_b
        question.option_c = option_c
        question.option_d = option_d
        question.correct_option = correct_option
        question.marks = marks

        db.session.commit()
        flash('Question updated successfully.', 'success')
        return redirect(url_for('admin.exam_questions', exam_id=test.id))

    return render_template('admin/edit_question.html', question=question, test=test)


@admin_bp.route('/question/<int:question_id>/delete', methods=['POST'])
def delete_question(question_id):
    """Delete a specific question from an examination."""
    question = db.session.get(Question, question_id)
    if not question:
        abort(404)

    test_id = question.test_id
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully from the examination.', 'info')
    return redirect(url_for('admin.exam_questions', exam_id=test_id))
