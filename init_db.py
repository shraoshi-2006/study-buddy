from database import engine, ensure_user_security_columns
from models import Base

Base.metadata.create_all(engine)
ensure_user_security_columns()

print("Database Created")
