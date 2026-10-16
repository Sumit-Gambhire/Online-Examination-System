import sys
from app import create_app, db
from app.models import User, Test, Question, Attempt, Answer

app = create_app()

with app.app_context():
    print("=== 1. Flask App Initialization & Registered Routes ===")
    rules = sorted([str(p) for p in app.url_map.iter_rules()])
    for r in rules:
        print(f"  {r}")

    print("\n=== 2. SQLite Tables & Relationships Check ===")
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Detected Tables:", tables)
    for table_name in tables:
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        print(f"  Table '{table_name}': {columns}")

    print("\n=== 3. Model Entities Count ===")
    print("  Users:", User.query.count())
    print("  Tests:", Test.query.count())
    print("  Questions:", Question.query.count())
    print("  Attempts:", Attempt.query.count())
    print("  Answers:", Answer.query.count())
