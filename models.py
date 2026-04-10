# models.py
import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(256), nullable=False)   # store hashed password
    full_name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)        # admin, lecturer, student

    # Relationships
    taught_modules = relationship("Module", foreign_keys="Module.lecturer_id", backref="lecturer")
    enrollments = relationship("ModuleEnrollment", back_populates="student")
    quizzes_created = relationship("Quiz", backref="creator")
    attempts = relationship("Attempt", back_populates="student")

class Module(Base):
    __tablename__ = "modules"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    lecturer_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    # Relationships
    enrollments = relationship("ModuleEnrollment", back_populates="module")
    quizzes = relationship("Quiz", backref="module")

class ModuleEnrollment(Base):
    __tablename__ = "module_enrollments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=False)

    student = relationship("User", back_populates="enrollments")
    module = relationship("Module", back_populates="enrollments")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=False)
    title = Column(String(200), nullable=False)
    questions = Column(JSON, nullable=False)        # list of question objects
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    attempts = relationship("Attempt", back_populates="quiz")

class Attempt(Base):
    __tablename__ = "attempts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, nullable=False)          # dict {question_id: answer}
    score = Column(Integer, nullable=True)
    comment = Column(String(500), nullable=True)
    graded = Column(Boolean, default=False)
    submitted_at = Column(DateTime, server_default=func.now())

    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="attempts")
