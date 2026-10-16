from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.models import db, Test, Question, Attempt, Answer

student_bp = Blueprint('student', __name__)

@student_bp.before_request
@login_required
def ensure_student():
    """Enforce role-based access control: Only student candidates can access student portal."""
    if current_user.is_admin:
        flash('Faculty administrators should use the Administrative Portal.', 'info')
        return redirect(url_for('admin.dashboard'))


@student_bp.route('/dashboard')
def dashboard():
    """Student dashboard overview showing active tests and completed attempts."""
    available_tests = Test.query.filter_by(is_published=True).all()
    past_attempts = Attempt.query.filter_by(user_id=current_user.id, status='Completed').order_by(Attempt.submitted_at.desc()).all()

    total_taken = len(past_attempts)
    passed_count = sum(1 for a in past_attempts if a.is_passed)
    average_score = round(sum(a.percentage for a in past_attempts) / total_taken, 1) if total_taken > 0 else 0.0

    return render_template(
        'student/dashboard.html',
        available_exams=available_tests,
        past_results=past_attempts,
        total_taken=total_taken,
        passed_count=passed_count,
        average_score=average_score
    )


@student_bp.route('/exams')
def exams():
    """List only published examinations available to the student."""
    available_tests = Test.query.filter_by(is_published=True).all()
    taken_test_ids = {a.test_id for a in Attempt.query.filter_by(user_id=current_user.id, status='Completed').all()}

    return render_template(
        'student/exams.html',
        available_exams=available_tests,
        taken_exam_ids=taken_test_ids
    )


@student_bp.route('/exam/<int:exam_id>/instructions')
def instructions(exam_id):
    """Pre-examination instructions and rules before starting an attempt."""
    test = db.session.get(Test, exam_id)
    if not test or not test.is_published:
        flash('This examination is currently not available or not published.', 'warning')
        return redirect(url_for('student.exams'))

    questions_count = len(test.questions)
    return render_template(
        'student/instructions.html',
        exam=test,
        questions_count=questions_count
    )


@student_bp.route('/exam/<int:exam_id>/start', methods=['POST'])
def start_exam(exam_id):
    """
    Initiate or resume an examination attempt.
    CONCURRENCY & DUPLICATE PROTECTION:
    - If an active unexpired attempt already exists for this test, resume it.
    - If an active attempt has expired, finalize it and redirect to result.
    - Otherwise, create a single new Attempt record in database.
    """
    test = db.session.get(Test, exam_id)
    if not test or not test.is_published:
        flash('This examination is currently inactive or unpublished.', 'warning')
        return redirect(url_for('student.exams'))

    if not test.questions:
        flash('This examination does not have any questions configured yet.', 'warning')
        return redirect(url_for('student.exams'))

    # Check for existing 'In Progress' attempt
    active_attempt = Attempt.query.filter_by(
        user_id=current_user.id,
        test_id=test.id,
        status='In Progress'
    ).first()

    if active_attempt:
        if active_attempt.is_expired():
            # Finalize expired attempt
            active_attempt.status = 'Completed'
            active_attempt.submitted_at = datetime.utcnow()
            db.session.commit()
            flash('Your previous attempt reached its time limit and was finalized.', 'info')
            return redirect(url_for('student.view_result', result_id=active_attempt.id))
        else:
            flash('Resuming your active examination session.', 'info')
            return redirect(url_for('student.take_attempt', attempt_id=active_attempt.id))

    # Create fresh Attempt
    new_attempt = Attempt(
        user_id=current_user.id,
        test_id=test.id,
        started_at=datetime.utcnow(),
        score=0.0,
        status='In Progress'
    )
    db.session.add(new_attempt)
    db.session.flush()

    # Pre-initialize Answer rows for each question to support reliable autosave & state restoration
    for q in test.questions:
        ans = Answer(
            attempt_id=new_attempt.id,
            question_id=q.id,
            selected_option=None,
            is_correct=False,
            marks_awarded=0.0,
            is_marked_for_review=False
        )
        db.session.add(ans)

    db.session.commit()
    return redirect(url_for('student.take_attempt', attempt_id=new_attempt.id))


@student_bp.route('/attempt/<int:attempt_id>/take')
def take_attempt(attempt_id):
    """
    Active examination testing interface.
    SECURITY & INTEGRITY:
    - Verifies attempt ownership.
    - Enforces server-side deadline.
    - Restores all previously saved answers and review markers on reload.
    - Never exposes correct answers in student DOM.
    """
    attempt = db.session.get(Attempt, attempt_id)
    if not attempt:
        abort(404)

    # Ownership validation
    if attempt.user_id != current_user.id:
        abort(403)

    test = attempt.test
    if not test:
        abort(404)

    # Prevent accessing completed attempts as live tests
    if attempt.status == 'Completed':
        flash('This attempt has already been submitted and finalized.', 'info')
        return redirect(url_for('student.view_result', result_id=attempt.id))

    # Enforce server-side deadline
    if attempt.is_expired():
        _finalize_and_grade_attempt(attempt)
        flash('Time expired! Your examination was automatically submitted and evaluated.', 'warning')
        return redirect(url_for('student.view_result', result_id=attempt.id))

    # Calculate remaining time in seconds based on server start time
    remaining_seconds = attempt.remaining_seconds

    questions = Question.query.filter_by(test_id=test.id).order_by(Question.id.asc()).all()
    # Sanitize questions to exclude correct_option
    sanitized_questions = [q.to_student_dict() for q in questions]

    # Map saved answers and review flags
    saved_answers = {}
    for ans in attempt.answers:
        saved_answers[ans.question_id] = {
            'selected': ans.selected_option or '',
            'is_review': ans.is_marked_for_review
        }

    return render_template(
        'student/take_exam.html',
        attempt=attempt,
        exam=test,
        questions=sanitized_questions,
        remaining_seconds=remaining_seconds,
        saved_answers=saved_answers
    )


# Keep friendly alias /student/exam/<id>/take redirecting to start/resume logic
@student_bp.route('/exam/<int:exam_id>/take', methods=['GET', 'POST'])
def take_exam_alias(exam_id):
    """Convenience endpoint ensuring seamless backward-compatibility."""
    test = db.session.get(Test, exam_id)
    if not test:
        abort(404)

    active_attempt = Attempt.query.filter_by(
        user_id=current_user.id,
        test_id=test.id,
        status='In Progress'
    ).first()

    if active_attempt:
        return redirect(url_for('student.take_attempt', attempt_id=active_attempt.id))
    return redirect(url_for('student.instructions', exam_id=test.id))


@student_bp.route('/attempt/<int:attempt_id>/save-answer', methods=['POST'])
def save_answer(attempt_id):
    """
    AJAX endpoint for real-time autosave of answers and review status.
    Ensures answers are restored on page reload.
    """
    attempt = db.session.get(Attempt, attempt_id)
    if not attempt or attempt.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized attempt'}), 403

    if attempt.status != 'In Progress':
        return jsonify({'success': False, 'error': 'Attempt already completed'}), 400

    if attempt.is_expired():
        _finalize_and_grade_attempt(attempt)
        return jsonify({'success': False, 'expired': True, 'error': 'Time expired'}), 400

    question_id = request.form.get('question_id', type=int)
    selected_option = request.form.get('selected_option', '').strip().upper()
    is_review = True if request.form.get('is_review') in ['1', 'true', True] else False

    # Validate question belongs to this test
    question = db.session.get(Question, question_id)
    if not question or question.test_id != attempt.test_id:
        return jsonify({'success': False, 'error': 'Invalid question ID for this test'}), 400

    if selected_option not in ['A', 'B', 'C', 'D', '']:
        return jsonify({'success': False, 'error': 'Invalid option value'}), 400

    # Find or create answer record
    answer = Answer.query.filter_by(attempt_id=attempt.id, question_id=question.id).first()
    if not answer:
        answer = Answer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option=selected_option if selected_option else None,
            is_marked_for_review=is_review
        )
        db.session.add(answer)
    else:
        answer.selected_option = selected_option if selected_option else None
        answer.is_marked_for_review = is_review

    db.session.commit()
    return jsonify({
        'success': True,
        'question_id': question.id,
        'selected_option': answer.selected_option or '',
        'is_review': answer.is_marked_for_review
    })


@student_bp.route('/attempt/<int:attempt_id>/submit', methods=['POST'])
def submit_attempt(attempt_id):
    """
    Finalize and grade examination attempt.
    SECURITY & ROBUSTNESS:
    - Prevents double submission.
    - Server-side deadline enforcement.
    - Transactional grading.
    - Never trusts client-side scores.
    """
    attempt = db.session.get(Attempt, attempt_id)
    if not attempt:
        abort(404)

    if attempt.user_id != current_user.id:
        abort(403)

    # Prevent duplicate grading if attempt was already completed
    if attempt.status == 'Completed':
        flash('This attempt was already submitted and graded.', 'info')
        return redirect(url_for('student.view_result', result_id=attempt.id))

    # Enforce server-side deadline
    if attempt.is_expired():
        _finalize_and_grade_attempt(attempt)
        flash('The examination time limit has expired. Your saved answers were automatically submitted and evaluated.', 'warning')
        return redirect(url_for('student.view_result', result_id=attempt.id))

    test = attempt.test
    questions = Question.query.filter_by(test_id=test.id).all()

    try:
        # Save any options sent with the final submit form payload
        for q in questions:
            field_name = f'question_{q.id}'
            form_opt = request.form.get(field_name, '').strip().upper()
            review_field = f'review_{q.id}'
            form_review = True if request.form.get(review_field) in ['1', 'true', True] else False

            ans = Answer.query.filter_by(attempt_id=attempt.id, question_id=q.id).first()
            if not ans:
                ans = Answer(attempt_id=attempt.id, question_id=q.id)
                db.session.add(ans)

            if form_opt in ['A', 'B', 'C', 'D']:
                ans.selected_option = form_opt
            if form_review:
                ans.is_marked_for_review = True

        db.session.flush()

        # Grade attempt on server
        _finalize_and_grade_attempt(attempt)
        flash('Examination submitted successfully! Your automated score is ready.', 'success')
        return redirect(url_for('student.view_result', result_id=attempt.id))

    except Exception as e:
        db.session.rollback()
        flash('An error occurred during submission. Please try submitting again.', 'danger')
        return redirect(url_for('student.take_attempt', attempt_id=attempt.id))


def _finalize_and_grade_attempt(attempt):
    """Internal helper to calculate marks strictly on the server and finalize attempt."""
    if attempt.status == 'Completed':
        return

    test = attempt.test
    questions = Question.query.filter_by(test_id=test.id).all()
    total_score = 0.0

    for q in questions:
        ans = Answer.query.filter_by(attempt_id=attempt.id, question_id=q.id).first()
        if not ans:
            ans = Answer(
                attempt_id=attempt.id,
                question_id=q.id,
                selected_option=None,
                is_correct=False,
                marks_awarded=0.0,
                is_marked_for_review=False
            )
            db.session.add(ans)

        if ans.selected_option and ans.selected_option.strip():
            sel_opt = ans.selected_option.strip().upper()
            corr_opt = q.correct_option.strip().upper()
            is_correct = (sel_opt == corr_opt)
            ans.is_correct = is_correct
            ans.marks_awarded = float(q.marks) if is_correct else 0.0
            total_score += ans.marks_awarded
        else:
            ans.selected_option = None
            ans.is_correct = False
            ans.marks_awarded = 0.0

    attempt.score = round(total_score, 2)
    attempt.status = 'Completed'
    if not attempt.submitted_at:
        attempt.submitted_at = datetime.utcnow()
    db.session.commit()


@student_bp.route('/result/<int:result_id>')
def view_result(result_id):
    """Detailed score summary and question breakdown for a completed test attempt."""
    attempt = db.session.get(Attempt, result_id)
    if not attempt:
        abort(404)

    # Security check: Students can only view their own test attempts
    if attempt.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    # Security check: Do not reveal results/answers while attempt is still in progress
    if attempt.status != 'Completed':
        flash('This examination is currently in progress. Answers and evaluation are only accessible after submission.', 'warning')
        return redirect(url_for('student.take_attempt', attempt_id=attempt.id))

    return render_template(
        'student/result.html',
        attempt=attempt,
        exam=attempt.test
    )


@student_bp.route('/history')
def history():
    """
    Complete chronological submission history for the logged-in student candidate.
    Supports search filtering, status filtering, and pagination.
    """
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all').strip().lower()

    # Base query: strictly scoped to the logged-in student's completed attempts
    query = Attempt.query.filter_by(user_id=current_user.id, status='Completed')

    if search_query:
        query = query.join(Test).filter(Test.title.ilike(f'%{search_query}%'))

    # Retrieve all completed attempts for global statistics
    all_user_attempts = Attempt.query.filter_by(user_id=current_user.id, status='Completed').all()
    total_exams = len(all_user_attempts)
    passed_exams = sum(1 for a in all_user_attempts if a.is_passed is True)
    failed_exams = sum(1 for a in all_user_attempts if a.is_passed is False)

    # Order chronologically descending
    query = query.order_by(Attempt.submitted_at.desc())

    # Paginate (10 attempts per page)
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    results = pagination.items

    # In-memory filter for status tabs if requested
    if status_filter == 'passed':
        results = [r for r in results if r.is_passed is True]
    elif status_filter == 'failed':
        results = [r for r in results if r.is_passed is False]

    return render_template(
        'student/history.html',
        results=results,
        pagination=pagination,
        search_query=search_query,
        status_filter=status_filter,
        total_exams=total_exams,
        passed_exams=passed_exams,
        failed_exams=failed_exams
    )
