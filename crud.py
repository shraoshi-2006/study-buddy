from database import SessionLocal
from models import User


def create_user(name, email, password):

    db = SessionLocal()

    user = User(
        name=name,
        email=email,
        password=password
    )

    db.add(user)

    db.commit()

    db.refresh(user)

    db.close()

    return user


def get_user(email):

    db = SessionLocal()

    user = db.query(User).filter(
        User.email == email
    ).first()

    db.close()

    return user