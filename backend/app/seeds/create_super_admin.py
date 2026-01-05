from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password

SUPER_ADMIN_EMAIL = "admin@gmail.com"
SUPER_ADMIN_PASSWORD = "12345678"  # change later
SUPER_ADMIN_ROLE = "admin"

def run():
    db: Session = SessionLocal()

    admin = db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first()
    if admin:
        print("✅ Super Admin already exists")
        return

    # hash safely
    hashed_password = hash_password(SUPER_ADMIN_PASSWORD)

    admin = User(
        email=SUPER_ADMIN_EMAIL,
        password_hash=hashed_password,
        role=SUPER_ADMIN_ROLE,
        is_active=True
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    print("🎉 Super Admin created successfully")
    print(f"📧 Email: {SUPER_ADMIN_EMAIL}")
    print(f"🔑 Password: {SUPER_ADMIN_PASSWORD}")

if __name__ == "__main__":
    run()
