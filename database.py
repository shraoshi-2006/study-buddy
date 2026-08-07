from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///studybuddy.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def ensure_user_security_columns():
    """Add the OTP security fields to an existing SQLite database, if needed."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("users")}
    additions = {
        "otp_hash": "VARCHAR(255)",
        "otp_purpose": "VARCHAR(30)",
        "otp_expires_at": "DATETIME",
        "otp_attempts": "INTEGER NOT NULL DEFAULT 0",
        "otp_last_sent_at": "DATETIME",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
