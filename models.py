from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)

    name = Column(String(100))

    email = Column(
        String(200),
        unique=True,
        nullable=False
    )

    password = Column(String(255))

    # OTPs are stored only as hashes and are always short-lived.
    otp_hash = Column(String(255), nullable=True)
    otp_purpose = Column(String(30), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, nullable=False, default=0)
    otp_last_sent_at = Column(DateTime, nullable=True)

    chats = relationship(
        "Chat",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    pdfs = relationship(
        "PDF",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    flashcards = relationship(
        "Flashcard",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    performances = relationship(
        "Performance",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    role = Column(String(20))
    content = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    chat_id = Column(Integer, ForeignKey("chats.id"))

    chat = relationship("Chat", back_populates="messages")


class PDF(Base):
    __tablename__ = "pdfs"

    id = Column(Integer, primary_key=True)

    filename = Column(String(255))
    filepath = Column(String(255))

    summary = Column(Text)

    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="pdfs")


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True)

    question = Column(Text)

    answer = Column(Text)

    topic = Column(String(200))

    favorite = Column(Integer, default=0)

    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="flashcards")


class Performance(Base):
    __tablename__ = "performance"

    id = Column(Integer, primary_key=True)

    quiz_score = Column(Integer)

    revision_completed = Column(Integer)

    study_time = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="performances")
