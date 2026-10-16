# Online Examination System (College Mini Project)

A production-grade, modular web application for creating, managing, taking, and automatically grading academic examinations, built with **Python Flask**, **SQLite**, and **Jinja2**.

---

## 📖 Project Overview & Key Features

The **Online Examination System** provides a complete end-to-end computer-based testing workflow for educational institutions, split into two dedicated role-based portals:

### 🎓 Student Candidate Portal
1. **Catalog of Published Examinations:** Browse active, published academic examinations with duration, question count, and maximum points.
2. **Pre-Examination Instructions & Honor Code:** Comprehensive rules, time limits, passing criteria, and honor code confirmation before beginning.
3. **Timed Examination Interface:**
   - Multiple Choice Questions (MCQ) with 4 selectable options.
   - Server-synchronized countdown timer that prevents client-side clock tampering.
   - Interactive **Question Palette** showing live status: *Answered*, *Marked for Review*, *Answered & Marked for Review*, and *Not Attempted*.
   - Free jump navigation and inline *Previous / Next* controls.
   - "Clear Choice" button to unselect an option.
   - "Mark for Review" bookmarking capability.
4. **Resilient Real-Time Autosave:**
   - Background AJAX synchronization to SQLite with visual status indicator (`Saving...`, `Saved`).
   - Full state restoration across accidental browser reloads or tab closures.
5. **Interactive Submit Confirmation:**
   - Modal dialog displaying summary statistics (answered, reviewed, unanswered counts) with warnings before finalization.
   - Automatic submission upon countdown expiry.
6. **Instant Automated Evaluation & Breakdown:**
   - Server-side grading comparing candidate responses against the master answer key.
   - Overall score, maximum marks, percentage, accuracy rate, and time taken.
   - Conditional **PASSED / FAILED** badge when an administrator-configured threshold exists.
   - Complete question-by-question review with official answer keys (strictly hidden during the live exam).
7. **Comprehensive Submission History:**
   - Historical log of all completed assessments.
   - Status filtering (*All*, *Passed*, *Failed*), search by test title, and pagination.
   - Strict student data isolation (students can only access their own results).

### 🛠️ Faculty Administrator Portal
1. **Administrative Analytics Dashboard:**
   - Real-time counts of registered students, total tests, published tests, and completed submissions.
   - Recent test submissions log.
2. **Examination Management (CRUD):**
   - Create, edit, and delete assessments.
   - Configure title, syllabus guidelines, duration in minutes (1–360), maximum marks, and optional passing benchmark percentage (0–100%).
   - Publish/unpublish toggle to control student visibility.
   - Safe deletion protection preventing removal of tests with existing student attempt records.
3. **Question Bank Management:**
   - Add, edit, and delete 4-option objective MCQ test items.
   - Configure individual question point weights and assign correct answer keys (`A`, `B`, `C`, or `D`).
4. **Security & Academic Integrity:**
   - Strict zero-trust grading computed exclusively on the server.
   - Zero-dependency session-based CSRF protection.
   - PBKDF2/scrypt password hashing.
   - Concurrent attempt prevention and double-submission protection.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+ & Flask 3.1
- **Database:** SQLite 3 (zero external database configuration required)
- **ORM & Data Layer:** Flask-SQLAlchemy 3.1 & SQLAlchemy 2.1
- **Authentication & Sessions:** Flask-Login 0.6 & Werkzeug 3.1
- **Frontend / Templating:** HTML5, Vanilla CSS3 (Custom Design System), Vanilla JavaScript (ES6+), Jinja2
- **Icons & Typography:** Font Awesome 6.5 & Google Fonts (Inter)

---

## 📁 Folder Structure

```text
Online-Examination-System/
├── app/
│   ├── __init__.py               # Application factory, CSRF protection, sample seeding, CLI commands
│   ├── models.py                 # SQLAlchemy relational schema (User, Test, Question, Attempt, Answer)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main.py               # Landing page & public informational routes
│   │   ├── auth.py               # Student registration, candidate/admin login & logout
│   │   ├── student.py            # Active testing, autosave, submission, results, and history
│   │   └── admin.py              # Faculty dashboard, exam management, and question authoring
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css         # Complete responsive design system, palette, and modals
│   │   └── js/
│   │       └── main.js           # Client-side countdown timer, autosave engine, palette sync, modal
│   └── templates/
│       ├── base.html             # Global base template
│       ├── student_layout.html   # Student dashboard layout with sidebar navigation
│       ├── admin_layout.html     # Administrator layout with faculty navigation
│       ├── main/
│       │   ├── index.html        # Public landing page
│       │   └── about.html        # System overview
│       ├── auth/
│       │   ├── register.html     # Student self-registration
│       │   ├── login.html        # Candidate login
│       │   └── admin_login.html  # Faculty administrator login
│       ├── student/
│       │   ├── dashboard.html    # Student dashboard with KPIs and active exams
│       │   ├── exams.html        # Available examinations catalog
│       │   ├── instructions.html # Pre-exam guidelines & honor code
│       │   ├── take_exam.html    # Fullscreen examination interface with timer & palette
│       │   ├── result.html       # Automated score breakdown & question review
│       │   └── history.html      # Submission history with search, filters & pagination
│       └── admin/
│           ├── dashboard.html    # Faculty metrics dashboard
│           ├── exams.html        # Exam catalog & create test form
│           ├── edit_exam.html    # Exam metadata editor
│           └── questions.html    # MCQ question bank manager
├── instance/
│   └── exam_system.db           # SQLite relational database
├── requirements.txt              # Production Python package requirements
├── run.py                        # Application entrypoint & CLI server runner
├── test_exam_module.py           # Integration test suite for exam flow & security
├── test_grading_and_results.py   # Test suite for grading calculations & result history
└── test_quality_audit.py         # Master quality audit test suite (14-point audit)
```

---

## ⚙️ Python Installation Requirements

- **Python Version:** Python 3.10, 3.11, 3.12, or 3.13
- **Operating System:** Windows, macOS, or Linux
- **Package Manager:** `pip`

---

## 💻 Virtual Environment Setup & Installation

### Step 1: Clone or Navigate to the Workspace
```bash
cd "Online-Examination-System"
```

### Step 2: Create a Virtual Environment (Recommended)
```bash
# Windows PowerShell / Command Prompt
python -m venv venv

# macOS / Linux
python3 -m venv venv
```

### Step 3: Activate the Virtual Environment
```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows Command Prompt (cmd)
.\venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🗄️ Database Initialization

The SQLite database file (`instance/exam_system.db`) and all required tables are **initialized automatically** when the application starts up. The system also seeds a sample curriculum assessment (*Computer Science & Web Development Fundamentals*) with objective questions if the database is fresh.

To reset or inspect the database manually at any time:
```bash
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database initialized!')"
```

---

## 🔑 How to Create the First Administrator

To provision a Faculty Administrator account with complete management privileges:

### Option A: Interactive CLI Command (Recommended)
Run the built-in management command:
```bash
flask create-admin
```
Follow the interactive prompts:
```text
Full Name: Prof. Alan Turing
College Email: admin@college.edu
Password: (hidden input)
Confirm Password: (hidden input)
```

### Option B: Python Run CLI
```bash
python run.py create-admin
```

---

## 🚀 How to Start the Application

Run the application runner:
```bash
python run.py
```
Or use the Flask CLI:
```bash
flask run --port=5000
```

The web server will start locally:
- **Application URL:** `http://127.0.0.1:5000`
- **Student Portal:** `http://127.0.0.1:5000/auth/login`
- **Administrator Portal:** `http://127.0.0.1:5000/auth/admin-login`

---

## 🧪 How to Run Automated Tests

The repository includes comprehensive automated test suites that test all features against the live SQLite database:

### 1. Run the Master Quality Audit Suite
Tests all 14 quality audit requirements including startup, registration, RBAC, CRUD, grading, and transactions:
```bash
python test_quality_audit.py
```

### 2. Run the Examination Flow & Security Suite
Tests attempt initiation, timer calculation, autosave, reload restoration, and parameter tampering:
```bash
python test_exam_module.py
```

### 3. Run the Grading Engine & Result System Suite
Tests manual calculation examples, percentage rounding, unanswered zero marks, and pass/fail thresholds:
```bash
python test_grading_and_results.py
```

---

## 🎯 Demo Walkthrough

### 👨‍🏫 Faculty Administrator Demo Flow
1. Open `http://127.0.0.1:5000/auth/admin-login`.
2. Log in with your administrator credentials (or click **Auto-fill Admin Demo**).
3. From the **Faculty Dashboard**, view active performance KPIs.
4. Navigate to **Examination Management** (`/admin/exams`):
   - Enter title, duration in minutes, total marks, and passing threshold (e.g., `40%`).
   - Check **Publish immediately** and click **Save & Proceed to Add Questions**.
5. On the **Question Authoring Page** (`/admin/exam/<id>/questions`):
   - Add objective MCQ questions specifying Options A, B, C, D, the correct key, and question points.
6. Toggle test publication status or edit exam metadata as needed.

### 👩‍🎓 Student Candidate Demo Flow
1. Open `http://127.0.0.1:5000/auth/register` and register a new candidate profile.
2. Log in at `http://127.0.0.1:5000/auth/login` to enter the **Student Dashboard**.
3. Click **Browse Catalog** (`/student/exams`) to view all published examinations.
4. Click **Instructions & Start** (`/student/exam/<id>/instructions`):
   - Review duration, questions count, point scale, and honor code rules.
   - Check the agreement checkbox and click **I Agree & Begin Examination**.
5. Inside the **Examination Interface** (`/student/attempt/<id>/take`):
   - Observe the real-time countdown timer synchronized with the server.
   - Select option cards for MCQs; observe the top-bar **Autosaved** indicator synchronizing in the background.
   - Mark challenging questions for review using the **Mark for Review** toggle.
   - Use the **Question Palette** on the right sidebar to jump between questions.
   - Reload the webpage to verify that all choices and review markers are safely restored from SQLite.
6. Click **Submit Exam**:
   - Inspect the interactive confirmation modal displaying counts of answered, reviewed, and unanswered questions.
   - Click **Yes, Submit Now** to finalize.
7. Review your **Evaluation Result Page** (`/student/result/<id>`):
   - View your final score, percentage, passing status, time taken, and accuracy breakdown.
   - Inspect each question's correct answer key and explanation.
8. Click **View Full History** (`/student/history`) to see historical submissions with status filters and search.
