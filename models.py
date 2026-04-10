# models.py
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, JSON, DateTime, func
from sqlalchemy.orm import relationship
import uuid

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    taught_modules = relationship("Module", foreign_keys="Module.lecturer_id", back_populates="lecturer")
    enrollments = relationship("ModuleEnrollment", back_populates="student")   # ✅ added
    quizzes_created = relationship("Quiz", back_populates="creator")            # ✅ added
    attempts = relationship("Attempt", back_populates="student")                # ✅ added

class Module(Base):
    __tablename__ = "modules"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    lecturer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    lecturer = relationship("User", foreign_keys=[lecturer_id], back_populates="taught_modules")
    enrollments = relationship("ModuleEnrollment", back_populates="module")    # ✅ added
    quizzes = relationship("Quiz", back_populates="module")                    # ✅ added

class ModuleEnrollment(Base):
    __tablename__ = "module_enrollments"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=False)

    # Relationships
    student = relationship("User", back_populates="enrollments")
    module = relationship("Module", back_populates="enrollments")

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    module_id = Column(String(36), ForeignKey("modules.id"), nullable=False)
    title = Column(String(200), nullable=False)
    questions = Column(JSON, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    module = relationship("Module", back_populates="quizzes")
    creator = relationship("User", back_populates="quizzes_created")
    attempts = relationship("Attempt", back_populates="quiz")

class Attempt(Base):
    __tablename__ = "attempts"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Integer, nullable=True)
    total_score = Column(Integer, nullable=True)
    graded = Column(Boolean, default=False)
    has_essay = Column(Boolean, default=False)
    comment = Column(String(500), nullable=True)
    graded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    submitted_at = Column(DateTime, server_default=func.now())

    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="attempts")
