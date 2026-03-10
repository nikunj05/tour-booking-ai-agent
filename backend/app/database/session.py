from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from sqlalchemy.exc import SQLAlchemyError

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, max_overflow=20)
SessionLocal = sessionmaker(bind=engine)
def get_db():
    db = None
    try:
        db = SessionLocal()
        yield db

    except SQLAlchemyError:
        print("Database connection error")
        raise RuntimeError("DB_CONNECTION_FAILED")

    finally:
        if db:
            db.close()