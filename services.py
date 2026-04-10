# services.py (SQLAlchemy version)
from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import joinedload
from database import db_session
from models import User, Module, ModuleEnrollment, Quiz, Attempt

# ---------- helpers (mostly unchanged) ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_b64, digest_b64 = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

# ---------- replacements for list operations ----------
def get_list(model):
    """Return all rows of a model as list of dicts."""
    return [row.to_dict() for row in db_session.query(model).all()]

def find_by_id(model, item_id: str):
    """Return a single model instance or None."""
    return db_session.query(model).filter_by(id=item_id).first()

def save(obj):
    db_session.add(obj)
    db_session.commit()
    return obj

# Add to_dict methods to models for easy JSON serialization
def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "password_hash": u.password,
        "full_name": u.full_name,
        "role": u.role,
        "created_at": u.created_at.isoformat() if u.created_at else now_iso(),
    }

def _module_to_dict(m: Module) -> dict:
    return {
        "id": m.id,
        "code": m.code,
        "name": m.name,
        "lecturer_id": m.lecturer_id,
        "student_ids": [e.student_id for e in m.enrollments],
        "created_at": m.created_at.isoformat() if m.created_at else now_iso(),
    }

def _quiz_to_dict(q: Quiz) -> dict:
    return {
        "id": q.id,
        "module_id": q.module_id,
        "title": q.title,
        "questions": q.questions,
        "created_by": q.created_by,
        "published": True,
        "created_at": q.created_at.isoformat() if q.created_at else now_iso(),
    }

def _attempt_to_dict(a: Attempt) -> dict:
    return {
        "id": a.id,
        "quiz_id": a.quiz_id,
        "student_id": a.student_id,
        "answers": a.answers,
        "auto_score": a.score if a.graded and not a.has_essay else 0,  # we'll compute later
        "final_score": a.score or 0,
        "total_score": a.total_score or 0,
        "status": "reviewed" if a.graded else ("pending_review" if a.has_essay else "graded"),
        "has_essay": a.has_essay,
        "lecturer_comment": a.comment or "",
        "graded_by": a.graded_by,
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else now_iso(),
    }

User.to_dict = _user_to_dict
Module.to_dict = _module_to_dict
Quiz.to_dict = _quiz_to_dict
Attempt.to_dict = _attempt_to_dict

# ---------- public functions (keep signatures) ----------
def get_public_modules(store) -> list[dict[str, Any]]:
    modules = db_session.query(Module).all()
    lecturers = {u.id: u for u in db_session.query(User).filter_by(role="lecturer")}
    public = []
    for module in modules:
        lecturer = lecturers.get(module.lecturer_id)
        public.append({
            "id": module.id,
            "code": module.code,
            "name": module.name,
            "lecturer_name": lecturer.full_name if lecturer else "Unassigned",
        })
    return public

def seed_demo_data(store) -> None:
    if db_session.query(User).count() > 0:
        return  # already seeded

    # Create admin
    admin = User(
        id="u_admin",
        username="admin",
        password=hash_password("admin123"),
        full_name="System Admin",
        role="admin",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)

    # Create lecturer
    lecturer = User(
        id="u_lecturer_1",
        username="lecturer",
        password=hash_password("lecturer123"),
        full_name="Demo Lecturer",
        role="lecturer",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(lecturer)

    # Create student
    student = User(
        id="u_student_1",
        username="student",
        password=hash_password("student123"),
        full_name="Demo Student",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(student)
    db_session.commit()

    # Create module
    module = Module(
        id="m_prog101",
        code="PROG101",
        name="Introduction to Programming",
        lecturer_id=lecturer.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(module)
    db_session.commit()

    # Enroll student
    enrollment = ModuleEnrollment(student_id=student.id, module_id=module.id)
    db_session.add(enrollment)

    # Create quiz
    questions = [
        {
            "id": "q1",
            "type": "multiple_choice",
            "text": "Which symbol is commonly used to start a comment in Python?",
            "options": ["//", "#", "<!--", "%%"],
            "correct_index": 1,
            "points": 10,
        },
        {
            "id": "q2",
            "type": "multiple_choice",
            "text": "Which data type stores whole numbers?",
            "options": ["int", "str", "list", "dict"],
            "correct_index": 0,
            "points": 10,
        },
        {
            "id": "q3",
            "type": "true_false",
            "text": "Python is a dynamically typed language.",
            "correct_answer": "true",
            "points": 5,
        },
        {
            "id": "q4",
            "type": "short_answer",
            "text": "What keyword is used to define a function in Python?",
            "correct_answers": ["def"],
            "points": 5,
        },
    ]
    quiz = Quiz(
        id="q_prog101_1",
        module_id=module.id,
        title="Programming Basics Quiz",
        questions=questions,
        created_by=lecturer.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(quiz)
    db_session.commit()

    # Create attempt
    attempt = Attempt(
        id="a_demo_1",
        quiz_id=quiz.id,
        student_id=student.id,
        answers={"q1": 1, "q2": 0, "q3": "true", "q4": "def"},
        score=30,
        total_score=30,
        graded=True,
        has_essay=False,
        comment="Welcome to the system.",
        graded_by=lecturer.id,
        submitted_at=datetime.now(timezone.utc),
    )
    db_session.add(attempt)
    db_session.commit()

def authenticate(store, username: str, password: str) -> dict[str, Any] | None:
    user = db_session.query(User).filter_by(username=username.strip().lower()).first()
    if user and verify_password(password, user.password):
        return user.to_dict()
    return None

def create_user(store, username: str, password: str, full_name: str, role: str) -> dict[str, Any]:
    if db_session.query(User).filter_by(username=username.strip()).first():
        raise ValueError("Username already exists.")
    if role not in {"admin", "lecturer", "student"}:
        raise ValueError("Invalid role.")

    user = User(
        id=new_id("u"),
        username=username.strip(),
        password=hash_password(password),
        full_name=full_name.strip() or username.strip(),
        role=role,
        created_at=datetime.now(timezone.utc),
    )
    save(user)
    return user.to_dict()

def create_module(store, code: str, name: str, lecturer_id: str) -> dict[str, Any]:
    lecturer = find_by_id(User, lecturer_id)
    if not lecturer or lecturer.role != "lecturer":
        raise ValueError("Selected lecturer does not exist.")
    if db_session.query(Module).filter_by(code=code.strip().upper()).first():
        raise ValueError("Module code already exists.")

    module = Module(
        id=new_id("m"),
        code=code.strip().upper(),
        name=name.strip(),
        lecturer_id=lecturer_id,
        created_at=datetime.now(timezone.utc),
    )
    save(module)
    return module.to_dict()

def assign_lecturer_to_module(store, module_id: str, lecturer_id: str) -> dict[str, Any]:
    module = find_by_id(Module, module_id)
    lecturer = find_by_id(User, lecturer_id)
    if not module:
        raise ValueError("Module not found.")
    if not lecturer or lecturer.role != "lecturer":
        raise ValueError("Lecturer not found.")
    module.lecturer_id = lecturer_id
    db_session.commit()
    return module.to_dict()

def enroll_student_in_module(store, student_id: str, module_id: str) -> dict[str, Any]:
    student = find_by_id(User, student_id)
    module = find_by_id(Module, module_id)
    if not student or student.role != "student":
        raise ValueError("Student not found.")
    if not module:
        raise ValueError("Module not found.")

    existing = db_session.query(ModuleEnrollment).filter_by(student_id=student_id, module_id=module_id).first()
    if not existing:
        enrollment = ModuleEnrollment(student_id=student_id, module_id=module_id)
        save(enrollment)
    return module.to_dict()

def get_user_modules(store, user: dict[str, Any]) -> list[dict[str, Any]]:
    """Return modules relevant to the logged-in user."""
    if user["role"] == "admin":
        return [m.to_dict() for m in db_session.query(Module).all()]
    if user["role"] == "lecturer":
        return [m.to_dict() for m in db_session.query(Module).filter_by(lecturer_id=user["id"]).all()]
    # student
    modules = db_session.query(Module).join(ModuleEnrollment).filter(ModuleEnrollment.student_id == user["id"]).all()
    return [m.to_dict() for m in modules]

def create_quiz(store, module_id: str, title: str, questions: list[dict[str, Any]], created_by: str) -> dict[str, Any]:
    module = find_by_id(Module, module_id)
    creator = find_by_id(User, created_by)
    if not module:
        raise ValueError("Module not found.")
    if not creator or creator.role not in {"lecturer", "admin"}:
        raise ValueError("Only lecturers or admins can create quizzes.")
    if creator.role == "lecturer" and module.lecturer_id != creator.id:
        raise ValueError("Lecturer can only create quizzes for their own modules.")

    # Clean and validate questions (same as original)
    cleaned_questions = []
    for idx, q in enumerate(questions, 1):
        text = str(q.get("text", "")).strip()
        q_type = str(q.get("type", "multiple_choice")).strip().lower()
        points = int(q.get("points", 1))
        if not text or points <= 0:
            raise ValueError(f"Question {idx} must have text and positive points.")
        if q_type not in {"multiple_choice", "true_false", "short_answer", "essay"}:
            q_type = "multiple_choice"
        q_data = {"id": new_id("q"), "type": q_type, "text": text, "points": points}
        if q_type == "multiple_choice":
            options = [str(opt).strip() for opt in q.get("options", []) if str(opt).strip()]
            correct_index = int(q.get("correct_index", 0))
            if len(options) < 2:
                raise ValueError(f"Question {idx} (Multiple Choice) must have at least 2 options.")
            if correct_index < 0 or correct_index >= len(options):
                raise ValueError(f"Question {idx} has an invalid correct answer index.")
            q_data["options"] = options
            q_data["correct_index"] = correct_index
        elif q_type == "true_false":
            correct_answer = str(q.get("correct_answer", "true")).lower()
            if correct_answer not in {"true", "false"}:
                raise ValueError(f"Question {idx} (True/False) must have true or false as correct answer.")
            q_data["correct_answer"] = correct_answer
        elif q_type == "short_answer":
            correct_answers = q.get("correct_answers", [])
            if isinstance(correct_answers, str):
                correct_answers = [correct_answers]
            correct_answers = [str(a).strip().lower() for a in correct_answers if str(a).strip()]
            if not correct_answers:
                raise ValueError(f"Question {idx} (Short Answer) must have at least one correct answer.")
            q_data["correct_answers"] = correct_answers
        elif q_type == "essay":
            q_data["instructions"] = str(q.get("instructions", "")).strip()
        cleaned_questions.append(q_data)

    quiz = Quiz(
        id=new_id("quiz"),
        module_id=module_id,
        title=title.strip(),
        questions=cleaned_questions,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    save(quiz)
    return quiz.to_dict()

def get_quiz_by_id(store, quiz_id: str) -> dict[str, Any] | None:
    quiz = find_by_id(Quiz, quiz_id)
    return quiz.to_dict() if quiz else None

def get_module_by_id(store, module_id: str) -> dict[str, Any] | None:
    module = find_by_id(Module, module_id)
    return module.to_dict() if module else None

def get_attempts(store) -> list[dict[str, Any]]:
    return [a.to_dict() for a in db_session.query(Attempt).all()]

def submit_quiz(store, student_id: str, quiz_id: str, answers: dict[str, Any]) -> dict[str, Any]:
    student = find_by_id(User, student_id)
    quiz = find_by_id(Quiz, quiz_id)
    if not student or student.role != "student":
        raise ValueError("Student not found.")
    if not quiz:
        raise ValueError("Quiz not found.")

    # Check enrollment
    module = find_by_id(Module, quiz.module_id)
    enrollment = db_session.query(ModuleEnrollment).filter_by(student_id=student_id, module_id=module.id).first()
    if not enrollment:
        raise ValueError("You are not enrolled in this module.")

    # Check for existing attempt
    existing = db_session.query(Attempt).filter_by(quiz_id=quiz_id, student_id=student_id).first()
    if existing:
        raise ValueError("You have already submitted this quiz.")

    total_score = 0
    auto_score = 0
    has_essay = False
    answer_map = {}

    for q in quiz.questions:
        qid = q["id"]
        q_type = q.get("type", "multiple_choice")
        selected = answers.get(qid, None)
        points = int(q["points"])
        total_score += points

        if q_type == "multiple_choice":
            try:
                selected_index = int(selected) if selected is not None else None
            except (TypeError, ValueError):
                selected_index = None
            answer_map[qid] = selected_index
            if selected_index is not None and selected_index == q.get("correct_index", -1):
                auto_score += points
        elif q_type == "true_false":
            selected_answer = str(selected).lower() if selected else None
            answer_map[qid] = selected_answer
            if selected_answer and selected_answer == q.get("correct_answer"):
                auto_score += points
        elif q_type == "short_answer":
            selected_text = str(selected).strip().lower() if selected else ""
            answer_map[qid] = selected_text
            correct_answers = [str(a).lower() for a in q.get("correct_answers", [])]
            if selected_text and selected_text in correct_answers:
                auto_score += points
        elif q_type == "essay":
            answer_map[qid] = str(selected).strip() if selected else ""
            has_essay = True

    final_score = auto_score if not has_essay else 0
    status = "pending_review" if has_essay else "graded"

    attempt = Attempt(
        id=new_id("attempt"),
        quiz_id=quiz_id,
        student_id=student_id,
        answers=answer_map,
        score=final_score,
        total_score=total_score,
        graded=not has_essay,
        has_essay=has_essay,
        comment="",
        graded_by=None,
        submitted_at=datetime.now(timezone.utc),
    )
    save(attempt)
    # to_dict expects auto_score and final_score; we'll adjust to_dict to compute
    return attempt.to_dict()

def grade_attempt(store, lecturer_id: str, attempt_id: str, score: int, comment: str = "") -> dict[str, Any]:
    lecturer = find_by_id(User, lecturer_id)
    attempt = find_by_id(Attempt, attempt_id)
    if not lecturer or lecturer.role != "lecturer":
        raise ValueError("Lecturer not found.")
    if not attempt:
        raise ValueError("Attempt not found.")

    quiz = find_by_id(Quiz, attempt.quiz_id)
    module = find_by_id(Module, quiz.module_id)
    if module.lecturer_id != lecturer_id:
        raise ValueError("You can only grade quizzes in your own module.")

    max_score = attempt.total_score
    if score < 0 or score > max_score:
        raise ValueError("Score must be within the valid range.")

    attempt.score = score
    attempt.graded_by = lecturer_id
    attempt.comment = comment.strip()
    attempt.graded = True
    db_session.commit()
    return attempt.to_dict()

def build_student_report(store, student_id: str) -> dict[str, Any]:
    student = find_by_id(User, student_id)
    if not student:
        raise ValueError("Student not found.")

    modules = db_session.query(Module).join(ModuleEnrollment).filter(ModuleEnrollment.student_id == student_id).all()
    report_modules = []
    for module in modules:
        quizzes_in_module = db_session.query(Quiz).filter_by(module_id=module.id).all()
        attempts_in_module = db_session.query(Attempt).filter(
            Attempt.student_id == student_id,
            Attempt.quiz_id.in_([q.id for q in quizzes_in_module])
        ).all()
        quiz_rows = []
        for quiz in quizzes_in_module:
            attempt = next((a for a in attempts_in_module if a.quiz_id == quiz.id), None)
            quiz_rows.append({
                "quiz_id": quiz.id,
                "title": quiz.title,
                "status": "attempted" if attempt else "not attempted",
                "score": attempt.score if attempt else 0,
                "total_score": attempt.total_score if attempt else sum(q["points"] for q in quiz.questions),
                "submitted_at": attempt.submitted_at.isoformat() if attempt else None,
            })
        scores = [a.score for a in attempts_in_module if a.score is not None]
        average = round(sum(scores) / len(scores), 2) if scores else 0.0
        report_modules.append({
            "module_id": module.id,
            "code": module.code,
            "name": module.name,
            "quiz_count": len(quizzes_in_module),
            "attempt_count": len(attempts_in_module),
            "average_score": average,
            "quizzes": quiz_rows,
        })

    all_attempts = db_session.query(Attempt).filter_by(student_id=student_id).all()
    overall_average = round(sum(a.score for a in all_attempts if a.score is not None) / len(all_attempts), 2) if all_attempts else 0.0

    return {
        "student": student.to_dict(),
        "overall": {
            "attempts": len(all_attempts),
            "average_score": overall_average,
        },
        "modules": report_modules,
    }

def build_lecturer_report(store, lecturer_id: str) -> dict[str, Any]:
    lecturer = find_by_id(User, lecturer_id)
    if not lecturer:
        raise ValueError("Lecturer not found.")

    modules = db_session.query(Module).filter_by(lecturer_id=lecturer_id).all()
    report_modules = []
    for module in modules:
        quizzes_in_module = db_session.query(Quiz).filter_by(module_id=module.id).all()
        attempts_in_module = db_session.query(Attempt).filter(Attempt.quiz_id.in_([q.id for q in quizzes_in_module])).all()
        students_enrolled = db_session.query(User).join(ModuleEnrollment).filter(ModuleEnrollment.module_id == module.id).all()
        student_attempts = {}
        for a in attempts_in_module:
            student_attempts.setdefault(a.student_id, []).append(a)
        report_students = []
        for student in students_enrolled:
            attempts = student_attempts.get(student.id, [])
            scores = [a.score for a in attempts if a.score is not None]
            report_students.append({
                "student_id": student.id,
                "username": student.username,
                "full_name": student.full_name,
                "attempt_count": len(attempts),
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            })
        module_scores = [a.score for a in attempts_in_module if a.score is not None]
        report_modules.append({
            "module_id": module.id,
            "code": module.code,
            "name": module.name,
            "quiz_count": len(quizzes_in_module),
            "student_count": len(students_enrolled),
            "attempt_count": len(attempts_in_module),
            "average_score": round(sum(module_scores) / len(module_scores), 2) if module_scores else 0.0,
            "students": report_students,
        })

    all_attempts = []
    for m in modules:
        quizzes = db_session.query(Quiz).filter_by(module_id=m.id).all()
        all_attempts.extend(db_session.query(Attempt).filter(Attempt.quiz_id.in_([q.id for q in quizzes])).all())
    overall_scores = [a.score for a in all_attempts if a.score is not None]

    return {
        "lecturer": lecturer.to_dict(),
        "overall": {
            "modules": len(modules),
            "attempts": len(all_attempts),
            "average_score": round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0.0,
        },
        "modules": report_modules,
    }

def flatten_student_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    student = report["student"]
    for module in report["modules"]:
        for quiz in module["quizzes"]:
            rows.append({
                "student_username": student["username"],
                "student_name": student["full_name"],
                "module_code": module["code"],
                "module_name": module["name"],
                "quiz_title": quiz["title"],
                "status": quiz["status"],
                "score": quiz["score"],
                "total_score": quiz["total_score"],
                "submitted_at": quiz["submitted_at"] or "",
            })
    return rows

def flatten_lecturer_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    lecturer = report["lecturer"]
    for module in report["modules"]:
        for student in module["students"]:
            rows.append({
                "lecturer_username": lecturer["username"],
                "lecturer_name": lecturer["full_name"],
                "module_code": module["code"],
                "module_name": module["name"],
                "student_username": student["username"],
                "student_name": student["full_name"],
                "attempt_count": student["attempt_count"],
                "average_score": student["average_score"],
            })
    return rows

def export_rows_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()

def export_raw_csv(items: list[dict[str, Any]]) -> str:
    return export_rows_csv(items)

def export_payload(store, kind: str, format_name: str, user: dict[str, Any] | None = None) -> tuple[str, str]:
    kind = kind.lower()
    format_name = format_name.lower()

    if kind == "users":
        payload = get_list(User)
    elif kind == "modules":
        payload = get_list(Module)
    elif kind == "quizzes":
        payload = get_list(Quiz)
    elif kind == "attempts":
        payload = get_list(Attempt)
    elif kind == "student-report":
        if not user or user.get("role") != "student":
            raise ValueError("Student report export is only available for students.")
        payload = flatten_student_report(build_student_report(store, user["id"]))
    elif kind == "lecturer-report":
        if not user or user.get("role") != "lecturer":
            raise ValueError("Lecturer report export is only available for lecturers.")
        payload = flatten_lecturer_report(build_lecturer_report(store, user["id"]))
    else:
        raise ValueError("Unsupported export type.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{kind}_{timestamp}"

    if format_name == "json":
        return json.dumps(payload, indent=2, ensure_ascii=False), f"{filename}.json"
    if format_name == "csv":
        if isinstance(payload, list):
            return export_rows_csv(payload), f"{filename}.csv"
        raise ValueError("CSV export requires tabular data.")
    raise ValueError("Unsupported export format.")
# ---------- helpers for app.py ----------
def get_all_users(store=None) -> list[dict[str, Any]]:
    """Return all users as list of dicts."""
    return [u.to_dict() for u in db_session.query(User).all()]

def get_all_modules(store=None) -> list[dict[str, Any]]:
    return [m.to_dict() for m in db_session.query(Module).all()]

def get_all_quizzes(store=None) -> list[dict[str, Any]]:
    return [q.to_dict() for q in db_session.query(Quiz).all()]

def get_all_attempts(store=None) -> list[dict[str, Any]]:
    return [a.to_dict() for a in db_session.query(Attempt).all()]

def get_module_students(store, module_id: str) -> list[dict[str, Any]]:
    """Return list of student dicts enrolled in a module."""
    module = find_by_id(Module, module_id)
    if not module:
        return []
    students = []
    for enrollment in module.enrollments:
        student = enrollment.student
        students.append(student.to_dict())
    return students

def get_quizzes_by_module(store, module_id: str) -> list[dict[str, Any]]:
    """Return list of quiz dicts for a given module."""
    quizzes = db_session.query(Quiz).filter_by(module_id=module_id).all()
    return [q.to_dict() for q in quizzes]

def get_attempts_by_lecturer(store, lecturer_id: str) -> list[dict[str, Any]]:
    """Return all attempts for quizzes in modules taught by the lecturer."""
    modules = db_session.query(Module).filter_by(lecturer_id=lecturer_id).all()
    module_ids = [m.id for m in modules]
    quiz_ids = [q.id for q in db_session.query(Quiz).filter(Quiz.module_id.in_(module_ids)).all()]
    attempts = db_session.query(Attempt).filter(Attempt.quiz_id.in_(quiz_ids)).all()
    return [a.to_dict() for a in attempts]

def get_student_quizzes_with_attempts(store, student_id: str) -> list[dict[str, Any]]:
    """Return quizzes for modules the student is enrolled in, with attempt info."""
    # Get enrolled module ids
    module_ids = [e.module_id for e in db_session.query(ModuleEnrollment).filter_by(student_id=student_id).all()]
    quizzes = db_session.query(Quiz).filter(Quiz.module_id.in_(module_ids)).all()
    attempts = {a.quiz_id: a for a in db_session.query(Attempt).filter_by(student_id=student_id).all()}
    result = []
    for quiz in quizzes:
        attempt = attempts.get(quiz.id)
        result.append({
            **quiz.to_dict(),
            "attempted": attempt is not None,
            "attempt": attempt.to_dict() if attempt else None,
        })
    return result
