from __future__ import annotations

import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from passlib.context import CryptContext

from config import get_smtp_settings
from database import SessionLocal, ensure_user_security_columns
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
OTP_TTL = timedelta(minutes=10)
OTP_RESEND_DELAY = timedelta(seconds=60)
MAX_OTP_ATTEMPTS = 5
LOGIN_OTP = "login"
RESET_OTP = "password_reset"

# Applies non-destructive SQLite migrations for existing Study Buddy databases.
ensure_user_security_columns()


def _normalise_email(email: str) -> str:
    return (email or "").strip().casefold()


def _valid_email(email: str) -> bool:
    return bool(EMAIL_RE.fullmatch(email))


def _password_error(password: str) -> str | None:
    if not isinstance(password, str) or len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be 128 characters or fewer."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must include at least one letter and one number."
    return None


def register_user(name: str, email: str, password: str):
    name = (name or "").strip()
    email = _normalise_email(email)
    if not name or len(name) > 100:
        return False, "Enter a name between 1 and 100 characters."
    if not _valid_email(email):
        return False, "Enter a valid email address."
    if error := _password_error(password):
        return False, error

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return False, "Unable to create an account with those details."
        db.add(User(name=name, email=email, password=pwd_context.hash(password)))
        db.commit()
        return True, "Registration successful. You can now sign in."
    except Exception:
        db.rollback()
        return False, "Unable to create an account right now."
    finally:
        db.close()


def login_user(email: str, password: str):
    email = _normalise_email(email)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not pwd_context.verify(password or "", user.password):
            return False, "Invalid email or password."
        return True, user
    finally:
        db.close()


def send_email(to_email: str, otp: str, purpose: str) -> None:
    host, port, username, password, sender = get_smtp_settings()
    subject = "Study Buddy password reset code" if purpose == RESET_OTP else "Study Buddy sign-in code"
    action = "reset your password" if purpose == RESET_OTP else "sign in"
    message = MIMEText(
        f"Your Study Buddy code is: {otp}\n\n"
        f"Use it to {action}. It expires in 10 minutes.\n"
        "If you did not request this, you can ignore this email."
    )
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to_email

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(username, password)
        server.sendmail(sender, [to_email], message.as_string())


def _send_otp(email: str, purpose: str):
    """Issue a hashed, expiring, rate-limited OTP without disclosing account existence."""
    email = _normalise_email(email)
    generic = "If that email is registered, a code has been sent."
    if not _valid_email(email):
        return False, "Enter a valid email address."

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return True, generic

        now = datetime.utcnow()
        if user.otp_last_sent_at and now - user.otp_last_sent_at < OTP_RESEND_DELAY:
            return False, "Please wait one minute before requesting another code."

        otp = f"{secrets.randbelow(900_000) + 100_000:06d}"
        user.otp_hash = pwd_context.hash(otp)
        user.otp_purpose = purpose
        user.otp_expires_at = now + OTP_TTL
        user.otp_attempts = 0
        user.otp_last_sent_at = now
        db.commit()
        try:
            send_email(email, otp, purpose)
        except Exception:
            # Do not leave a usable code behind if delivery failed.
            user.otp_hash = None
            user.otp_purpose = None
            user.otp_expires_at = None
            user.otp_attempts = 0
            db.commit()
            return False, "Unable to send a code right now. Please try again later."
        return True, generic
    except Exception:
        db.rollback()
        return False, "Unable to send a code right now. Please try again later."
    finally:
        db.close()


def send_login_otp(email: str):
    return _send_otp(email, LOGIN_OTP)


def send_password_reset_otp(email: str):
    return _send_otp(email, RESET_OTP)


def _consume_otp(user: User, otp: str, purpose: str) -> bool:
    now = datetime.utcnow()
    valid = (
        user.otp_hash
        and user.otp_purpose == purpose
        and user.otp_expires_at
        and user.otp_expires_at >= now
        and (user.otp_attempts or 0) < MAX_OTP_ATTEMPTS
        and isinstance(otp, str)
        and otp.isdigit()
        and len(otp) == 6
        and pwd_context.verify(otp, user.otp_hash)
    )
    if valid:
        user.otp_hash = None
        user.otp_purpose = None
        user.otp_expires_at = None
        user.otp_attempts = 0
        return True

    user.otp_attempts = (user.otp_attempts or 0) + 1
    if user.otp_attempts >= MAX_OTP_ATTEMPTS or (user.otp_expires_at and user.otp_expires_at < now):
        user.otp_hash = None
        user.otp_purpose = None
        user.otp_expires_at = None
    return False


def verify_otp(email: str, otp: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == _normalise_email(email)).first()
        if not user:
            return False
        valid = _consume_otp(user, otp, LOGIN_OTP)
        db.commit()
        return valid
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def reset_password(email: str, otp: str, new_password: str):
    if error := _password_error(new_password):
        return False, error
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == _normalise_email(email)).first()
        if not user or not _consume_otp(user, otp, RESET_OTP):
            db.commit()
            return False, "Invalid or expired reset code."
        user.password = pwd_context.hash(new_password)
        db.commit()
        return True, "Password updated. You can now sign in."
    except Exception:
        db.rollback()
        return False, "Unable to reset the password right now."
    finally:
        db.close()
