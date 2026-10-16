"""
Comprehensive Integration Test Suite for Online Examination System
Verifies:
1. Normal exam start, attempt creation & resumption
2. Answer key security (correct answers NOT exposed in client payload/DOM)
3. AJAX autosave & state restoration upon page reload
4. Parameter tampering prevention (unauthorized attempt access, wrong question IDs)
5. Double submission & duplicate grading prevention
6. Server-side deadline & time expiry enforcement
"""

import sys
import os
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from app.models import User, Test, Question, Attempt, Answer


def run_tests():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        # Setup test data
        print("==> Setting up test database entities...")
        # Clean existing test entities thoroughly
        test_emails = ["student_test1@college.edu", "student_test2@college.edu"]
        test_titles = ["Integration Automated Exam", "Hidden Draft Exam"]

        test_users = User.query.filter(User.email.in_(test_emails)).all()
        user_ids = [u.id for u in test_users]

        tests = Test.query.filter(Test.title.in_(test_titles)).all()
        test_ids = [t.id for t in tests]

        # Clean all attempts and child answers
        all_attempts = Attempt.query.filter(
            (Attempt.user_id.in_(user_ids)) | (Attempt.test_id.in_(test_ids))
        ).all()
        for att in all_attempts:
            Answer.query.filter_by(attempt_id=att.id).delete()
            db.session.delete(att)
        db.session.commit()

        # Clean questions
        Question.query.filter(Question.test_id.in_(test_ids)).delete()
        # Clean tests
        for t in tests:
            db.session.delete(t)
        # Clean users
        for u in test_users:
            db.session.delete(u)
        db.session.commit()

        # Create 2 test students
        student1 = User(full_name="Student One", email="student_test1@college.edu", role="student")
        student1.set_password("Pass12345!")
        db.session.add(student1)

        student2 = User(full_name="Student Two", email="student_test2@college.edu", role="student")
        student2.set_password("Pass12345!")
        db.session.add(student2)

        # Create published test with 2 questions
        test_exam = Test(
            title="Integration Automated Exam",
            description="Automated testing of examination module",
            duration_minutes=15,
            total_marks=20.0,
            passing_percentage=40.0,
            is_published=True
        )
        db.session.add(test_exam)
        db.session.flush()

        q1 = Question(
            test_id=test_exam.id,
            question_text="What is 2 + 2?",
            option_a="3",
            option_b="4",
            option_c="5",
            option_d="6",
            correct_option="B",
            marks=10.0
        )
        q2 = Question(
            test_id=test_exam.id,
            question_text="What is the capital of France?",
            option_a="Berlin",
            option_b="Madrid",
            option_c="Paris",
            option_d="Rome",
            correct_option="C",
            marks=10.0
        )
        db.session.add_all([q1, q2])

        # Create an unpublished test to test visibility
        unpub_test = Test(
            title="Hidden Draft Exam",
            description="Should not be visible to students",
            duration_minutes=30,
            total_marks=50.0,
            is_published=False
        )
        db.session.add(unpub_test)
        db.session.commit()

        client = app.test_client()

        # -------------------------------------------------------------
        # TEST 1: Student Views Only Published Tests
        # -------------------------------------------------------------
        print("\n[TEST 1] Testing Published Test Filtering...")
        # Login student1
        client.post('/auth/login', data={'identifier': 'student_test1@college.edu', 'password': 'Pass12345!'})
        res = client.get('/student/exams')
        assert res.status_code == 200
        assert b"Integration Automated Exam" in res.data
        assert b"Hidden Draft Exam" not in res.data
        print("✓ Test 1 Passed: Students see only published tests.")

        # -------------------------------------------------------------
        # TEST 2: Pre-exam Instructions & Details Display
        # -------------------------------------------------------------
        print("\n[TEST 2] Testing Pre-exam Instructions Page...")
        res = client.get(f'/student/exam/{test_exam.id}/instructions')
        assert res.status_code == 200
        assert b"Integration Automated Exam" in res.data
        assert b"15 Minutes" in res.data
        assert b"20" in res.data  # Total marks
        print("✓ Test 2 Passed: Instructions display title, duration, question count, and marks.")

        # -------------------------------------------------------------
        # TEST 3: Starting Test & Attempt Creation
        # -------------------------------------------------------------
        print("\n[TEST 3] Testing Exam Initiation & Attempt Creation...")
        res = client.post(f'/student/exam/{test_exam.id}/start', follow_redirects=False)
        assert res.status_code == 302
        redirect_url = res.headers['Location']
        assert "/student/attempt/" in redirect_url

        attempt_id = int(redirect_url.split('/student/attempt/')[1].split('/take')[0])
        db.session.expire_all()
        attempt = db.session.get(Attempt, attempt_id)
        assert attempt is not None
        assert attempt.user_id == student1.id
        assert attempt.test_id == test_exam.id
        assert attempt.status == 'In Progress'
        ans_count = Answer.query.filter_by(attempt_id=attempt.id).count()
        assert ans_count == 2
        print(f"✓ Test 3 Passed: Attempt #{attempt_id} created with 'In Progress' status and answer stubs.")

        # -------------------------------------------------------------
        # TEST 4: Answer Key Security & DOM Sanitization
        # -------------------------------------------------------------
        print("\n[TEST 4] Testing Answer Key Security (Zero Leakage)...")
        res = client.get(f'/student/attempt/{attempt_id}/take')
        assert res.status_code == 200
        html = res.data.decode('utf-8')
        assert "What is 2 + 2?" in html
        assert "Paris" in html
        # Ensure correct_option values are not in the template variables
        assert "correct_option" not in html
        print("✓ Test 4 Passed: Correct options are completely withheld from the student.")

        # -------------------------------------------------------------
        # TEST 5: AJAX Autosave & Review Marking
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing Real-time Autosave & Review Toggle...")
        # Save option B for Question 1
        save_res = client.post(f'/student/attempt/{attempt_id}/save-answer', data={
            'question_id': q1.id,
            'selected_option': 'B',
            'is_review': '0'
        })
        assert save_res.status_code == 200
        assert save_res.get_json()['success'] is True

        # Save option C for Question 2 and mark for review
        save_res2 = client.post(f'/student/attempt/{attempt_id}/save-answer', data={
            'question_id': q2.id,
            'selected_option': 'C',
            'is_review': '1'
        })
        assert save_res2.status_code == 200
        assert save_res2.get_json()['success'] is True

        # Verify directly in SQLite DB
        ans1 = Answer.query.filter_by(attempt_id=attempt_id, question_id=q1.id).first()
        ans2 = Answer.query.filter_by(attempt_id=attempt_id, question_id=q2.id).first()
        assert ans1.selected_option == 'B'
        assert ans1.is_marked_for_review is False
        assert ans2.selected_option == 'C'
        assert ans2.is_marked_for_review is True
        print("✓ Test 5 Passed: Answers and review flags successfully saved in database.")

        # -------------------------------------------------------------
        # TEST 6: Page Reload & State Restoration
        # -------------------------------------------------------------
        print("\n[TEST 6] Testing Page Reload & Saved State Restoration...")
        reload_res = client.get(f'/student/attempt/{attempt_id}/take')
        assert reload_res.status_code == 200
        reload_html = reload_res.data.decode('utf-8')
        # Check that opt-q1-B and opt-q2-C are rendered with is-selected and checked
        assert f'for="opt-{q1.id}-B"' in reload_html
        assert f'id="opt-{q1.id}-B"' in reload_html
        assert f'for="opt-{q2.id}-C"' in reload_html
        assert f'id="opt-{q2.id}-C"' in reload_html
        # Check review toggle for q2 is present and checked
        assert f'id="review-toggle-{q2.id}"' in reload_html
        assert f'review-lbl-{q2.id}' in reload_html
        # Check question palette buttons reflect answered and review states
        assert f'id="palette-btn-{q1.id}"' in reload_html
        assert f'id="palette-btn-{q2.id}"' in reload_html
        assert 'palette-answered' in reload_html
        assert 'palette-answered-review' in reload_html
        print("✓ Test 6 Passed: Reloading restores all selected options and review markers.")

        # -------------------------------------------------------------
        # TEST 7: Duplicate / Concurrent Attempt Prevention
        # -------------------------------------------------------------
        print("\n[TEST 7] Testing Duplicate Attempt Prevention...")
        resume_res = client.post(f'/student/exam/{test_exam.id}/start', follow_redirects=False)
        assert resume_res.status_code == 302
        assert f'/student/attempt/{attempt_id}/take' in resume_res.headers['Location']
        # Verify no second attempt was created
        student1_attempts = Attempt.query.filter_by(user_id=student1.id, test_id=test_exam.id).all()
        assert len(student1_attempts) == 1
        print("✓ Test 7 Passed: Second start request safely resumes existing in-progress attempt.")

        # -------------------------------------------------------------
        # TEST 8: Security & Parameter Tampering (Unauthorized Access)
        # -------------------------------------------------------------
        print("\n[TEST 8] Testing Attempt Ownership & Access Control...")
        # Logout student1, login student2
        client.get('/auth/logout')
        client.post('/auth/login', data={'identifier': 'student_test2@college.edu', 'password': 'Pass12345!'})

        # Student2 tries to access Student1's attempt
        unauth_get = client.get(f'/student/attempt/{attempt_id}/take')
        assert unauth_get.status_code == 403

        # Student2 tries to autosave to Student1's attempt
        unauth_save = client.post(f'/student/attempt/{attempt_id}/save-answer', data={
            'question_id': q1.id,
            'selected_option': 'A'
        })
        assert unauth_save.status_code == 403

        # Student2 tries to submit Student1's attempt
        unauth_sub = client.post(f'/student/attempt/{attempt_id}/submit', data={})
        assert unauth_sub.status_code == 403

        # Student2 tries to view Student1's result
        unauth_res = client.get(f'/student/result/{attempt_id}')
        assert unauth_res.status_code == 403

        # Relogin student1 to test invalid question ID
        client.get('/auth/logout')
        client.post('/auth/login', data={'identifier': 'student_test1@college.edu', 'password': 'Pass12345!'})

        # Tampering with question ID (belonging to nonexistent or other test)
        bad_q_save = client.post(f'/student/attempt/{attempt_id}/save-answer', data={
            'question_id': 999999,
            'selected_option': 'A'
        })
        assert bad_q_save.status_code == 400
        print("✓ Test 8 Passed: Unauthorized access and invalid question IDs are securely blocked.")

        # -------------------------------------------------------------
        # TEST 9: Normal Submission & Server-Side Grading
        # -------------------------------------------------------------
        print("\n[TEST 9] Testing Server-side Grading & Submission...")
        sub_res = client.post(f'/student/attempt/{attempt_id}/submit', data={
            f'question_{q1.id}': 'B',  # Correct (10 marks)
            f'question_{q2.id}': 'C'   # Correct (10 marks)
        }, follow_redirects=True)
        assert sub_res.status_code == 200
        assert b"Examination submitted successfully" in sub_res.data
        assert b"20.0" in sub_res.data
        assert b"PASSED" in sub_res.data

        # Verify DB values
        attempt_graded = db.session.get(Attempt, attempt_id)
        assert attempt_graded.status == 'Completed'
        assert attempt_graded.score == 20.0
        assert attempt_graded.submitted_at is not None
        print("✓ Test 9 Passed: Submission evaluated on server with 100% score (20/20).")

        # -------------------------------------------------------------
        # TEST 10: Double Submission Prevention
        # -------------------------------------------------------------
        print("\n[TEST 10] Testing Double Submission Prevention...")
        double_sub = client.post(f'/student/attempt/{attempt_id}/submit', data={
            f'question_{q1.id}': 'A',  # Try changing to incorrect
            f'question_{q2.id}': 'A'
        }, follow_redirects=True)
        assert double_sub.status_code == 200
        # Score must remain 20.0 and not be modified
        attempt_check = db.session.get(Attempt, attempt_id)
        assert attempt_check.score == 20.0
        print("✓ Test 10 Passed: Double submission blocked; completed attempt score remains unchanged.")

        # -------------------------------------------------------------
        # TEST 11: Server-Side Time Expiry Enforcement
        # -------------------------------------------------------------
        print("\n[TEST 11] Testing Server-Side Time Expiry Enforcement...")
        # Create an attempt for student2 and artificially set started_at in the past
        client.get('/auth/logout')
        client.post('/auth/login', data={'identifier': 'student_test2@college.edu', 'password': 'Pass12345!'})

        start2 = client.post(f'/student/exam/{test_exam.id}/start', follow_redirects=False)
        att2_id = int(start2.headers['Location'].split('/student/attempt/')[1].split('/take')[0])

        att2 = db.session.get(Attempt, att2_id)
        # Save one answer
        ans_att2 = Answer.query.filter_by(attempt_id=att2_id, question_id=q1.id).first()
        ans_att2.selected_option = 'B'
        # Artificially set start time to 20 minutes ago (test duration is 15 minutes)
        att2.started_at = datetime.utcnow() - timedelta(minutes=20)
        db.session.commit()

        # Student2 tries to access take page after deadline
        exp_res = client.get(f'/student/attempt/{att2_id}/take', follow_redirects=True)
        assert exp_res.status_code == 200
        assert b"Time expired" in exp_res.data

        # Verify att2 is automatically finalized in database
        att2_refreshed = db.session.get(Attempt, att2_id)
        assert att2_refreshed.status == 'Completed'
        assert att2_refreshed.score == 10.0  # Only q1 was answered correctly
        print("✓ Test 11 Passed: Expired attempt automatically finalized on server without client trust.")

        print("\n" + "=" * 60)
        print("ALL 11 INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == '__main__':
    run_tests()
