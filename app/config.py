import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..'))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam-system-secret-key-2026-secure-college-mini-project')
    
    # SQLite database stored in the instance directory
    INSTANCE_DIR = os.path.join(PROJECT_ROOT, 'instance')
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'exam_system.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session cookie security settings for local testing
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
