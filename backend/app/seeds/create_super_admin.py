from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.user import User
from app.core.security import hash_password
from app.models.company import Company

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
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    detail = Company(
        user_id=admin.id,
        company_name="Super Admin",
        phone="0000000000",
        status="active",
        currency="USD",
        country="america"
    )
    
    db.add(detail)
    db.commit()
    db.refresh(detail)

    print("🎉 Super Admin created successfully")
    print(f"📧 Email: {SUPER_ADMIN_EMAIL}")
    print(f"🔑 Password: {SUPER_ADMIN_PASSWORD}")
    print(f"status: {detail.status}")

if __name__ == "__main__":
    run()
