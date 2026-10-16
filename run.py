import sys
import os
from app import create_app, db
from app.models import User

app = create_app()

if __name__ == '__main__':
    # CLI command helper: python run.py create-admin
    if len(sys.argv) > 1 and sys.argv[1] == 'create-admin':
        with app.app_context():
            print("=== Secure Administrator Provisioning ===")
            name = input("Administrator Full Name: ").strip()
            email = input("Administrator Email: ").strip().lower()
            import getpass
            pwd = getpass.getpass("Administrator Password: ")
            pwd_conf = getpass.getpass("Confirm Password: ")
            if pwd != pwd_conf:
                print("Error: Passwords do not match.")
                sys.exit(1)
            if len(pwd) < 6:
                print("Error: Password must be at least 6 characters.")
                sys.exit(1)
            if User.query.filter_by(email=email).first():
                print(f"Error: User with email '{email}' already exists.")
                sys.exit(1)
            admin = User(full_name=name, email=email, role='admin')
            admin.set_password(pwd)
            db.session.add(admin)
            db.session.commit()
            print(f"Success! Faculty Administrator '{email}' created successfully.")
            sys.exit(0)

    port = int(os.environ.get('PORT', 5000))
    print(f"==================================================")
    print(f" Online Examination System is running!")
    print(f" URL: http://127.0.0.1:{port}")
    print(f" To create an administrator: flask create-admin")
    print(f"==================================================")
    app.run(host='127.0.0.1', port=port, debug=True)
