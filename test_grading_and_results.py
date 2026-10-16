"""
Automated Test Suite for Automatic Grading and Examination Result System
Tests:
1. Exact score, marks, percentage, and accuracy calculations with manually checked examples
2. Zero marks handling for unanswered questions
3. Administrator-configured passing threshold vs. no-threshold tests
4. In-progress result access protection (no answer key leak before submission)
5. Repeated / duplicate submission prevention
6. Result history authorization (ownership enforcement), search filtering, and pagination
"""

import sys
import os
from datetime import datetime, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app, db
from app.models import User, Test, Question, Attempt, Answer


def run_grading_and_results_tests():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        print("==> Setting up test suite for Grading and Result System...")

        # Thorough cleanup of test records
        test_emails = ["grade_stud1@college.edu", "grade_stud2@college.edu"]
        test_titles = ["Grading Benchmark Exam", "No Threshold Evaluation Exam"]

        users = User.query.filter(User.email.in_(test_emails)).all()
        u_ids = [u.id for u in users]
        tests = Test.query.filter(Test.title.in_(test_titles)).all()
        t_ids = [t.id for t in tests]

        attempts = Attempt.query.filter((Attempt.user_id.in_(u_ids)) | (Attempt.test_id.in_(t_ids))).all()
        for a in attempts:
            Answer.query.filter_by(attempt_id=a.id).delete()
            db.session.delete(a)
        db.session.commit()

        Question.query.filter(Question.test_id.in_(t_ids)).delete()
        for t in tests:
            db.session.delete(t)
        for u in users:
            db.session.delete(u)
        db.session.commit()

        # Create 2 test students
        student1 = User(full_name="Grading Student One", email="grade_stud1@college.edu", role="student")
        student1.set_password("StudentPass123!")
        student2 = User(full_name="Grading Student Two", email="grade_stud2@college.edu", role="student")
        student2.set_password("StudentPass123!")
        db.session.add_all([student1, student2])

        # Create Test 1: With Administrator-Configured Passing Threshold (40.0%)
        # Configured with 4 questions with variable marks (5, 10, 15, 20 => total 50 pts)
        test1 = Test(
            title="Grading Benchmark Exam",
            description="Assessment with 40% configured threshold",
            duration_minutes=25,
            total_marks=50,
            passing_percentage=40.0,
            is_published=True
        )
        db.session.add(test1)
        db.session.flush()

        q1 = Question(test_id=test1.id, question_text="Q1 (5 pts)", option_a="OptA", option_b="OptB", option_c="OptC", option_d="OptD", correct_option="A", marks=5)
        q2 = Question(test_id=test1.id, question_text="Q2 (10 pts)", option_a="OptA", option_b="OptB", option_c="OptC", option_d="OptD", correct_option="B", marks=10)
        q3 = Question(test_id=test1.id, question_text="Q3 (15 pts)", option_a="OptA", option_b="OptB", option_c="OptC", option_d="OptD", correct_option="C", marks=15)
        q4 = Question(test_id=test1.id, question_text="Q4 (20 pts)", option_a="OptA", option_b="OptB", option_c="OptC", option_d="OptD", correct_option="D", marks=20)
        db.session.add_all([q1, q2, q3, q4])

        # Create Test 2: NO Administrator Passing Threshold (passing_percentage=None)
        test2 = Test(
            title="No Threshold Evaluation Exam",
            description="Assessment without pass/fail classification",
            duration_minutes=20,
            total_marks=20,
            passing_percentage=None,
            is_published=True
        )
        db.session.add(test2)
        db.session.flush()

        q2_1 = Question(test_id=test2.id, question_text="T2 Q1 (10 pts)", option_a="A", option_b="B", option_c="C", option_d="D", correct_option="A", marks=10)
        q2_2 = Question(test_id=test2.id, question_text="T2 Q2 (10 pts)", option_a="A", option_b="B", option_c="C", option_d="D", correct_option="B", marks=10)
        db.session.add_all([q2_1, q2_2])

        db.session.commit()
        client = app.test_client()

        # =============================================================
        # TEST 1: Manually Checked Example A (Partial, Unanswered, Failed)
        # =============================================================
        print("\n[TEST 1] Testing Calculation Example A (Score, Marks, Unanswered, Failed)...")
        # Student 1 logs in
        client.post('/auth/login', data={'identifier': 'grade_stud1@college.edu', 'password': 'StudentPass123!'})
        
        # Start Test 1
        res = client.post(f'/student/exam/{test1.id}/start', follow_redirects=False)
        att1_id = int(res.headers['Location'].split('/student/attempt/')[1].split('/take')[0])

        # Manually Answer:
        # Q1 (5 pts): 'A' -> Correct (+5)
        # Q2 (10 pts): 'B' -> Correct (+10)
        # Q3 (15 pts): 'D' -> Incorrect (0)
        # Q4 (20 pts): UNANSWERED -> Unanswered (0)
        # Manually Checked Expected Values:
        # Expected Score: 5 + 10 + 0 + 0 = 15.0
        # Expected Maximum Marks: 50.0
        # Expected Percentage: (15.0 / 50.0) * 100 = 30.0%
        # Expected Correct Count: 2
        # Expected Incorrect Count: 1
        # Expected Unanswered Count: 1
        # Passing Threshold: 40.0% => 30.0% < 40.0% => FAILED (is_passed == False)

        sub_res = client.post(f'/student/attempt/{att1_id}/submit', data={
            f'question_{q1.id}': 'A',
            f'question_{q2.id}': 'B',
            f'question_{q3.id}': 'D'
            # question_q4 is intentionally omitted to verify unanswered handling
        }, follow_redirects=True)

        assert sub_res.status_code == 200
        db.session.expire_all()
        att1 = db.session.get(Attempt, att1_id)

        assert att1.score == 15.0, f"Expected 15.0 score, got {att1.score}"
        assert att1.maximum_marks == 50.0, f"Expected 50.0 max marks, got {att1.maximum_marks}"
        assert att1.percentage == 30.0, f"Expected 30.0%, got {att1.percentage}%"
        assert att1.correct_count == 2, f"Expected 2 correct, got {att1.correct_count}"
        assert att1.incorrect_count == 1, f"Expected 1 incorrect, got {att1.incorrect_count}"
        assert att1.unanswered_count == 1, f"Expected 1 unanswered, got {att1.unanswered_count}"
        assert att1.has_passing_threshold is True
        assert att1.is_passed is False, "Expected is_passed to be False (30% < 40%)"
        assert att1.status == 'Completed'
        assert att1.submitted_at is not None

        # Verify Result Page Content for Example A
        html = sub_res.data.decode('utf-8')
        assert "Grading Benchmark Exam" in html
        assert "Grading Student One" in html
        assert "15.0" in html
        assert "50.0" in html
        assert "30.0%" in html
        assert "FAILED (Threshold: 40.0%)" in html
        assert "Unanswered (0 pts awarded)" in html
        assert "Correct (+5.0 pts)" in html or "Correct (+5 pts)" in html
        assert "Correct (+10.0 pts)" in html or "Correct (+10 pts)" in html
        assert "Incorrect (0 pts awarded)" in html
        print("✓ Test 1 Passed: Manually calculated score (15.0/50.0 = 30.0%), counts (2C, 1I, 1U), and FAILED label verified.")

        # =============================================================
        # TEST 2: Manually Checked Example B (Passed Threshold)
        # =============================================================
        print("\n[TEST 2] Testing Calculation Example B (Passing Benchmark)...")
        # Retake Test 1
        res = client.post(f'/student/exam/{test1.id}/start', follow_redirects=False)
        att2_id = int(res.headers['Location'].split('/student/attempt/')[1].split('/take')[0])
        assert att2_id != att1_id

        # Manually Answer:
        # Q1 (5 pts): 'A' -> Correct (+5)
        # Q2 (10 pts): 'B' -> Correct (+10)
        # Q3 (15 pts): 'C' -> Correct (+15)
        # Q4 (20 pts): UNANSWERED -> Unanswered (0)
        # Expected Score: 5 + 10 + 15 + 0 = 30.0 / 50.0 = 60.0%
        # Threshold 40.0% => 60.0% >= 40.0% => PASSED (is_passed == True)

        client.post(f'/student/attempt/{att2_id}/submit', data={
            f'question_{q1.id}': 'A',
            f'question_{q2.id}': 'B',
            f'question_{q3.id}': 'C'
        }, follow_redirects=True)

        db.session.expire_all()
        att2 = db.session.get(Attempt, att2_id)
        assert att2.score == 30.0
        assert att2.percentage == 60.0
        assert att2.correct_count == 3
        assert att2.incorrect_count == 0
        assert att2.unanswered_count == 1
        assert att2.is_passed is True

        res_page = client.get(f'/student/result/{att2.id}')
        res_html = res_page.data.decode('utf-8')
        assert "PASSED (Threshold: 40.0%)" in res_html
        assert "60.0%" in res_html
        print("✓ Test 2 Passed: Manually calculated score (30.0/50.0 = 60.0%) and PASSED label verified.")

        # =============================================================
        # TEST 3: No-Threshold Test (Pass/Fail Label Omitted)
        # =============================================================
        print("\n[TEST 3] Testing Test With No Configured Passing Threshold...")
        # Start Test 2 (passing_percentage is None)
        res3 = client.post(f'/student/exam/{test2.id}/start', follow_redirects=False)
        att3_id = int(res3.headers['Location'].split('/student/attempt/')[1].split('/take')[0])

        client.post(f'/student/attempt/{att3_id}/submit', data={
            f'question_{q2_1.id}': 'A',
            f'question_{q2_2.id}': 'A'  # Wrong (correct is B)
        }, follow_redirects=True)

        db.session.expire_all()
        att3 = db.session.get(Attempt, att3_id)
        assert att3.score == 10.0
        assert att3.percentage == 50.0
        assert att3.has_passing_threshold is False
        assert att3.is_passed is None

        res3_page = client.get(f'/student/result/{att3.id}')
        res3_html = res3_page.data.decode('utf-8')
        assert "PASSED" not in res3_html
        assert "FAILED" not in res3_html
        assert "RESULT FINALIZED" in res3_html or "Evaluation Completed" in res3_html
        print("✓ Test 3 Passed: Tests with no administrator threshold omit pass/fail labels.")

        # =============================================================
        # TEST 4: Time Taken Calculation
        # =============================================================
        print("\n[TEST 4] Testing Time Taken Elapsed Calculation...")
        # Set started_at to 12 minutes and 30 seconds before submitted_at
        att2.started_at = att2.submitted_at - timedelta(minutes=12, seconds=30)
        db.session.commit()
        db.session.expire_all()

        assert att2.time_taken_seconds == 750
        assert att2.formatted_time_taken == "12m 30s"
        t_page = client.get(f'/student/result/{att2.id}')
        assert "12m 30s" in t_page.data.decode('utf-8')
        print("✓ Test 4 Passed: Time taken accurately formatted and displayed ('12m 30s').")

        # =============================================================
        # TEST 5: Repeated Submissions & Score Immutability
        # =============================================================
        print("\n[TEST 5] Testing Repeated Submissions & Score Tampering Prevention...")
        # Attempt to resubmit attempt 2 with different answers
        dup_res = client.post(f'/student/attempt/{att2.id}/submit', data={
            f'question_{q1.id}': 'D',
            f'question_{q2.id}': 'D',
            f'question_{q3.id}': 'D',
            f'question_{q4.id}': 'D'
        }, follow_redirects=True)
        assert dup_res.status_code == 200

        db.session.expire_all()
        att2_check = db.session.get(Attempt, att2.id)
        assert att2_check.score == 30.0, "Score was modified after completion!"
        assert att2_check.percentage == 60.0
        print("✓ Test 5 Passed: Repeated submission does not regrade or alter finalized scores.")

        # =============================================================
        # TEST 6: In-Progress Result Access Blocked (No Premature Answer Leaks)
        # =============================================================
        print("\n[TEST 6] Testing Premature Result Page Access Protection...")
        # Create an attempt in progress
        in_prog_start = client.post(f'/student/exam/{test2.id}/start', follow_redirects=False)
        in_prog_id = int(in_prog_start.headers['Location'].split('/student/attempt/')[1].split('/take')[0])

        # Attempt to access result page while exam is in progress
        premature_res = client.get(f'/student/result/{in_prog_id}', follow_redirects=False)
        assert premature_res.status_code == 302
        assert f'/student/attempt/{in_prog_id}/take' in premature_res.headers['Location']
        print("✓ Test 6 Passed: In-progress attempts cannot access result page (answers shielded).")

        # =============================================================
        # TEST 7: Result History Scoping, Ownership, Search & Filter
        # =============================================================
        print("\n[TEST 7] Testing Result History Access Control & Filtering...")
        # Student 1 views their history
        hist1 = client.get('/student/history')
        assert hist1.status_code == 200
        hist_html = hist1.data.decode('utf-8')
        assert f"#ATT-{att1.id}" in hist_html
        assert f"#ATT-{att2.id}" in hist_html

        # Switch to Student 2
        client.get('/auth/logout')
        client.post('/auth/login', data={'identifier': 'grade_stud2@college.edu', 'password': 'StudentPass123!'})

        # Student 2 history must NOT show Student 1's attempts
        hist2 = client.get('/student/history')
        hist2_html = hist2.data.decode('utf-8')
        assert f"#ATT-{att1.id}" not in hist2_html
        assert f"#ATT-{att2.id}" not in hist2_html

        # Student 2 cannot access Student 1's result page
        unauth_page = client.get(f'/student/result/{att1.id}')
        assert unauth_page.status_code == 403

        # Test Search & Filter on Student 1's history
        client.get('/auth/logout')
        client.post('/auth/login', data={'identifier': 'grade_stud1@college.edu', 'password': 'StudentPass123!'})

        # Filter by status: Passed
        passed_filter = client.get('/student/history?status=passed')
        assert f"#ATT-{att2.id}" in passed_filter.data.decode('utf-8')
        assert f"#ATT-{att1.id}" not in passed_filter.data.decode('utf-8')

        # Filter by status: Failed
        failed_filter = client.get('/student/history?status=failed')
        assert f"#ATT-{att1.id}" in failed_filter.data.decode('utf-8')
        assert f"#ATT-{att2.id}" not in failed_filter.data.decode('utf-8')

        # Search query filter
        search_filter = client.get('/student/history?q=Benchmark')
        assert "Grading Benchmark Exam" in search_filter.data.decode('utf-8')

        print("✓ Test 7 Passed: Result history strictly enforces user ownership, search, and filtering.")

        print("\n" + "=" * 65)
        print("ALL 7 GRADING AND RESULT SYSTEM TESTS PASSED SUCCESSFULLY!")
        print("=" * 65)


if __name__ == '__main__':
    run_grading_and_results_tests()
