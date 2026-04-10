
"""Business logic for the quiz system."""
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
from pathlib import Path
from typing import Any

from storage import DataStore


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Create a salted password hash that can be stored in JSON."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against the stored salted hash."""
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


def get_list(store: DataStore, name: str) -> list[dict[str, Any]]:
    data = store.load(name)
    return data if isinstance(data, list) else []


def save_list(store: DataStore, name: str, items: list[dict[str, Any]]) -> None:
    store.save(name, items)


def find_by_id(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def find_user_by_username(users: list[dict[str, Any]], username: str) -> dict[str, Any] | None:
    username = username.strip().lower()
    for user in users:
        if user.get("username", "").strip().lower() == username:
            return user
    return None


def get_public_modules(store: DataStore) -> list[dict[str, Any]]:
    """Modules returned to signup and public forms."""
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    lecturers = {u["id"]: u for u in users if u.get("role") == "lecturer"}
    public = []
    for module in modules:
        lecturer = lecturers.get(module.get("lecturer_id"))
        public.append({
            "id": module["id"],
            "code": module["code"],
            "name": module["name"],
            "lecturer_name": lecturer["full_name"] if lecturer else "Unassigned",
        })
    return public


def seed_demo_data(store: DataStore) -> None:
    """Create a usable starter system on the first run."""
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    quizzes = get_list(store, "quizzes")
    attempts = get_list(store, "attempts")

    changed = False

    if not find_user_by_username(users, "admin"):
        users.append({
            "id": "u_admin",
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "full_name": "System Admin",
            "role": "admin",
            "created_at": now_iso(),
        })
        changed = True

    lecturer = find_user_by_username(users, "lecturer")
    if not lecturer:
        lecturer = {
            "id": "u_lecturer_1",
            "username": "lecturer",
            "password_hash": hash_password("lecturer123"),
            "full_name": "Demo Lecturer",
            "role": "lecturer",
            "created_at": now_iso(),
        }
        users.append(lecturer)
        changed = True

    student = find_user_by_username(users, "student")
    if not student:
        student = {
            "id": "u_student_1",
            "username": "student",
            "password_hash": hash_password("student123"),
            "full_name": "Demo Student",
            "role": "student",
            "created_at": now_iso(),
        }
        users.append(student)
        changed = True

    if not modules:
        modules.append({
            "id": "m_prog101",
            "code": "PROG101",
            "name": "Introduction to Programming",
            "lecturer_id": lecturer["id"],
            "student_ids": [student["id"]],
            "created_at": now_iso(),
        })
        changed = True
    else:
        # Make sure the demo lecturer is assigned to at least one module.
        if not any(m.get("lecturer_id") == lecturer["id"] for m in modules):
            modules[0]["lecturer_id"] = lecturer["id"]
            changed = True

        # Make sure the demo student appears in at least one module.
        if not any(student["id"] in m.get("student_ids", []) for m in modules):
            modules[0].setdefault("student_ids", []).append(student["id"])
            changed = True

    if not quizzes:
        quizzes.append({
            "id": "q_prog101_1",
            "module_id": modules[0]["id"],
            "title": "Programming Basics Quiz",
            "created_by": lecturer["id"],
            "published": True,
            "created_at": now_iso(),
            "questions": [
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
            ],
        })
        changed = True

    if not attempts:
        attempts.append({
            "id": "a_demo_1",
            "quiz_id": quizzes[0]["id"],
            "student_id": student["id"],
            "answers": {"q1": 1, "q2": 0, "q3": "true", "q4": "def"},
            "auto_score": 30,
            "final_score": 30,
            "total_score": 30,
            "status": "graded",
            "has_essay": False,
            "lecturer_comment": "Welcome to the system.",
            "graded_by": lecturer["id"],
            "submitted_at": now_iso(),
        })
        changed = True

    if changed:
        save_list(store, "users", users)
        save_list(store, "modules", modules)
        save_list(store, "quizzes", quizzes)
        save_list(store, "attempts", attempts)


def authenticate(store: DataStore, username: str, password: str) -> dict[str, Any] | None:
    users = get_list(store, "users")
    user = find_user_by_username(users, username)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None


def create_user(
    store: DataStore,
    username: str,
    password: str,
    full_name: str,
    role: str,
) -> dict[str, Any]:
    users = get_list(store, "users")
    if find_user_by_username(users, username):
        raise ValueError("Username already exists.")

    if role not in {"admin", "lecturer", "student"}:
        raise ValueError("Invalid role.")

    user = {
        "id": new_id("u"),
        "username": username.strip(),
        "password_hash": hash_password(password),
        "full_name": full_name.strip() or username.strip(),
        "role": role,
        "created_at": now_iso(),
    }
    users.append(user)
    save_list(store, "users", users)
    return user


def create_module(
    store: DataStore,
    code: str,
    name: str,
    lecturer_id: str,
) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    lecturer = find_by_id(users, lecturer_id)
    if not lecturer or lecturer.get("role") != "lecturer":
        raise ValueError("Selected lecturer does not exist.")
    if any(m["code"].strip().lower() == code.strip().lower() for m in modules):
        raise ValueError("Module code already exists.")

    module = {
        "id": new_id("m"),
        "code": code.strip().upper(),
        "name": name.strip(),
        "lecturer_id": lecturer_id,
        "student_ids": [],
        "created_at": now_iso(),
    }
    modules.append(module)
    save_list(store, "modules", modules)
    return module


def assign_lecturer_to_module(store: DataStore, module_id: str, lecturer_id: str) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    module = find_by_id(modules, module_id)
    lecturer = find_by_id(users, lecturer_id)
    if not module:
        raise ValueError("Module not found.")
    if not lecturer or lecturer.get("role") != "lecturer":
        raise ValueError("Lecturer not found.")

    module["lecturer_id"] = lecturer_id
    save_list(store, "modules", modules)
    return module


def enroll_student_in_module(store: DataStore, student_id: str, module_id: str) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    student = find_by_id(users, student_id)
    module = find_by_id(modules, module_id)

    if not student or student.get("role") != "student":
        raise ValueError("Student not found.")
    if not module:
        raise ValueError("Module not found.")

    module.setdefault("student_ids", [])
    if student_id not in module["student_ids"]:
        module["student_ids"].append(student_id)

    save_list(store, "modules", modules)
    return module


def get_user_modules(store: DataStore, user: dict[str, Any]) -> list[dict[str, Any]]:
    """Return modules relevant to the logged-in user."""
    modules = get_list(store, "modules")
    if user["role"] == "admin":
        return modules
    if user["role"] == "lecturer":
        return [m for m in modules if m.get("lecturer_id") == user["id"]]
    return [m for m in modules if user["id"] in m.get("student_ids", [])]


def create_quiz(
    store: DataStore,
    module_id: str,
    title: str,
    questions: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    modules = get_list(store, "modules")
    users = get_list(store, "users")
    quizzes = get_list(store, "quizzes")

    module = find_by_id(modules, module_id)
    creator = find_by_id(users, created_by)
    if not module:
        raise ValueError("Module not found.")
    if not creator or creator.get("role") not in {"lecturer", "admin"}:
        raise ValueError("Only lecturers or admins can create quizzes.")
    if creator["role"] == "lecturer" and module.get("lecturer_id") != creator["id"]:
        raise ValueError("Lecturer can only create quizzes for their own modules.")

    cleaned_questions: list[dict[str, Any]] = []
    for idx, question in enumerate(questions, start=1):
        text = str(question.get("text", "")).strip()
        q_type = str(question.get("type", "multiple_choice")).strip().lower()
        points = int(question.get("points", 1))
        
        if not text or points <= 0:
            raise ValueError(f"Question {idx} must have text and positive points.")
        
        # Validate question type
        valid_types = {"multiple_choice", "true_false", "short_answer", "essay"}
        if q_type not in valid_types:
            q_type = "multiple_choice"
        
        q_data: dict[str, Any] = {
            "id": new_id("q"),
            "type": q_type,
            "text": text,
            "points": points,
        }
        
        # Handle type-specific fields
        if q_type == "multiple_choice":
            options = [str(opt).strip() for opt in question.get("options", []) if str(opt).strip()]
            correct_index = int(question.get("correct_index", 0))
            if len(options) < 2:
                raise ValueError(f"Question {idx} (Multiple Choice) must have at least 2 options.")
            if correct_index < 0 or correct_index >= len(options):
                raise ValueError(f"Question {idx} has an invalid correct answer index.")
            q_data["options"] = options
            q_data["correct_index"] = correct_index
        
        elif q_type == "true_false":
            correct_answer = str(question.get("correct_answer", "true")).lower()
            if correct_answer not in {"true", "false"}:
                raise ValueError(f"Question {idx} (True/False) must have true or false as correct answer.")
            q_data["correct_answer"] = correct_answer
        
        elif q_type == "short_answer":
            correct_answers = question.get("correct_answers", [])
            if isinstance(correct_answers, str):
                correct_answers = [correct_answers]
            correct_answers = [str(a).strip().lower() for a in correct_answers if str(a).strip()]
            if not correct_answers:
                raise ValueError(f"Question {idx} (Short Answer) must have at least one correct answer.")
            q_data["correct_answers"] = correct_answers
        
        elif q_type == "essay":
            # Essay questions don't have automated answers; they require manual grading
            q_data["instructions"] = str(question.get("instructions", "")).strip()
        
        cleaned_questions.append(q_data)

    quiz = {
        "id": new_id("quiz"),
        "module_id": module_id,
        "title": title.strip(),
        "questions": cleaned_questions,
        "created_by": created_by,
        "published": True,
        "created_at": now_iso(),
    }
    quizzes.append(quiz)
    save_list(store, "quizzes", quizzes)
    return quiz


def get_quiz_by_id(store: DataStore, quiz_id: str) -> dict[str, Any] | None:
    quizzes = get_list(store, "quizzes")
    return find_by_id(quizzes, quiz_id)


def get_module_by_id(store: DataStore, module_id: str) -> dict[str, Any] | None:
    modules = get_list(store, "modules")
    return find_by_id(modules, module_id)


def get_attempts(store: DataStore) -> list[dict[str, Any]]:
    return get_list(store, "attempts")


def submit_quiz(
    store: DataStore,
    student_id: str,
    quiz_id: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    quizzes = get_list(store, "quizzes")
    attempts = get_list(store, "attempts")

    student = find_by_id(users, student_id)
    quiz = find_by_id(quizzes, quiz_id)
    if not student or student.get("role") != "student":
        raise ValueError("Student not found.")
    if not quiz:
        raise ValueError("Quiz not found.")

    module = find_by_id(modules, quiz["module_id"])
    if not module or student_id not in module.get("student_ids", []):
        raise ValueError("You are not enrolled in this module.")

    existing = [a for a in attempts if a["quiz_id"] == quiz_id and a["student_id"] == student_id]
    if existing:
        raise ValueError("You have already submitted this quiz.")

    total_score = 0
    auto_score = 0
    pending_review = False
    answer_map: dict[str, Any] = {}
    
    for question in quiz["questions"]:
        qid = question["id"]
        q_type = question.get("type", "multiple_choice")
        selected = answers.get(qid, None)
        total_score += int(question["points"])
        
        # Auto-grade based on question type
        if q_type == "multiple_choice":
            try:
                selected_index = int(selected) if selected is not None else None
            except (TypeError, ValueError):
                selected_index = None
            answer_map[qid] = selected_index
            
            if selected_index is not None and selected_index == int(question.get("correct_index", -1)):
                auto_score += int(question["points"])
        
        elif q_type == "true_false":
            selected_answer = str(selected).lower() if selected else None
            answer_map[qid] = selected_answer
            
            if selected_answer and selected_answer == question.get("correct_answer"):
                auto_score += int(question["points"])
        
        elif q_type == "short_answer":
            selected_text = str(selected).strip().lower() if selected else ""
            answer_map[qid] = selected_text
            
            correct_answers = [str(a).lower() for a in question.get("correct_answers", [])]
            if selected_text and selected_text in correct_answers:
                auto_score += int(question["points"])
        
        elif q_type == "essay":
            # Essay answers are stored but not auto-graded
            answer_map[qid] = str(selected).strip() if selected else ""
            pending_review = True

    attempt = {
        "id": new_id("attempt"),
        "quiz_id": quiz_id,
        "student_id": student_id,
        "answers": answer_map,
        "auto_score": auto_score,
        "final_score": auto_score if not pending_review else 0,
        "total_score": total_score,
        "status": "pending_review" if pending_review else "graded",
        "has_essay": pending_review,
        "lecturer_comment": "",
        "graded_by": None,
        "submitted_at": now_iso(),
    }
    attempts.append(attempt)
    save_list(store, "attempts", attempts)
    return attempt


def grade_attempt(
    store: DataStore,
    lecturer_id: str,
    attempt_id: str,
    score: int,
    comment: str = "",
) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    quizzes = get_list(store, "quizzes")
    attempts = get_list(store, "attempts")

    lecturer = find_by_id(users, lecturer_id)
    if not lecturer or lecturer.get("role") != "lecturer":
        raise ValueError("Lecturer not found.")

    attempt = find_by_id(attempts, attempt_id)
    if not attempt:
        raise ValueError("Attempt not found.")

    quiz = find_by_id(quizzes, attempt["quiz_id"])
    if not quiz:
        raise ValueError("Quiz not found.")

    module = find_by_id(modules, quiz["module_id"])
    if not module or module.get("lecturer_id") != lecturer_id:
        raise ValueError("You can only grade quizzes in your own module.")

    max_score = int(attempt["total_score"])
    score = int(score)
    if score < 0 or score > max_score:
        raise ValueError("Score must be within the valid range.")

    # Calculate final score: auto_score + essay points awarded by lecturer
    attempt["final_score"] = score
    attempt["graded_by"] = lecturer_id
    attempt["lecturer_comment"] = comment.strip()
    attempt["status"] = "reviewed"
    save_list(store, "attempts", attempts)
    return attempt


def build_student_report(store: DataStore, student_id: str) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    quizzes = get_list(store, "quizzes")
    attempts = get_list(store, "attempts")

    student = find_by_id(users, student_id)
    if not student:
        raise ValueError("Student not found.")

    module_lookup = {m["id"]: m for m in modules}
    quiz_lookup = {q["id"]: q for q in quizzes}

    student_modules = [m for m in modules if student_id in m.get("student_ids", [])]
    report_modules = []

    for module in student_modules:
        module_quizzes = [q for q in quizzes if q["module_id"] == module["id"]]
        module_attempts = [a for a in attempts if a["student_id"] == student_id and quiz_lookup.get(a["quiz_id"], {}).get("module_id") == module["id"]]
        quiz_rows = []
        for quiz in module_quizzes:
            quiz_attempt = next((a for a in module_attempts if a["quiz_id"] == quiz["id"]), None)
            quiz_rows.append({
                "quiz_id": quiz["id"],
                "title": quiz["title"],
                "status": "attempted" if quiz_attempt else "not attempted",
                "score": quiz_attempt["final_score"] if quiz_attempt else 0,
                "total_score": quiz_attempt["total_score"] if quiz_attempt else sum(int(q["points"]) for q in quiz["questions"]),
                "submitted_at": quiz_attempt["submitted_at"] if quiz_attempt else None,
            })

        scores = [a["final_score"] for a in module_attempts]
        average = round(sum(scores) / len(scores), 2) if scores else 0.0

        report_modules.append({
            "module_id": module["id"],
            "code": module["code"],
            "name": module["name"],
            "quiz_count": len(module_quizzes),
            "attempt_count": len(module_attempts),
            "average_score": average,
            "quizzes": quiz_rows,
        })

    overall_attempts = [a for a in attempts if a["student_id"] == student_id]
    overall_average = round(sum(a["final_score"] for a in overall_attempts) / len(overall_attempts), 2) if overall_attempts else 0.0

    return {
        "student": {
            "id": student["id"],
            "username": student["username"],
            "full_name": student["full_name"],
        },
        "overall": {
            "attempts": len(overall_attempts),
            "average_score": overall_average,
        },
        "modules": report_modules,
    }


def build_lecturer_report(store: DataStore, lecturer_id: str) -> dict[str, Any]:
    users = get_list(store, "users")
    modules = get_list(store, "modules")
    quizzes = get_list(store, "quizzes")
    attempts = get_list(store, "attempts")

    lecturer = find_by_id(users, lecturer_id)
    if not lecturer:
        raise ValueError("Lecturer not found.")

    lecturer_modules = [m for m in modules if m.get("lecturer_id") == lecturer_id]
    student_lookup = {u["id"]: u for u in users if u.get("role") == "student"}

    report_modules = []
    for module in lecturer_modules:
        module_quizzes = [q for q in quizzes if q["module_id"] == module["id"]]
        module_attempts = [
            a for a in attempts
            if any(q["id"] == a["quiz_id"] for q in module_quizzes)
        ]
        enrolled_students = [student_lookup[sid] for sid in module.get("student_ids", []) if sid in student_lookup]

        attempts_by_student: dict[str, list[dict[str, Any]]] = {}
        for attempt in module_attempts:
            attempts_by_student.setdefault(attempt["student_id"], []).append(attempt)

        report_students = []
        for student in enrolled_students:
            student_attempts = attempts_by_student.get(student["id"], [])
            scores = [a["final_score"] for a in student_attempts]
            report_students.append({
                "student_id": student["id"],
                "username": student["username"],
                "full_name": student["full_name"],
                "attempt_count": len(student_attempts),
                "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
            })

        module_scores = [a["final_score"] for a in module_attempts]
        report_modules.append({
            "module_id": module["id"],
            "code": module["code"],
            "name": module["name"],
            "quiz_count": len(module_quizzes),
            "student_count": len(enrolled_students),
            "attempt_count": len(module_attempts),
            "average_score": round(sum(module_scores) / len(module_scores), 2) if module_scores else 0.0,
            "students": report_students,
        })

    overall_attempts = [
        a for a in attempts
        if any(q["module_id"] in [m["id"] for m in lecturer_modules] for q in quizzes if q["id"] == a["quiz_id"])
    ]
    overall_scores = [a["final_score"] for a in overall_attempts]

    return {
        "lecturer": {
            "id": lecturer["id"],
            "username": lecturer["username"],
            "full_name": lecturer["full_name"],
        },
        "overall": {
            "modules": len(lecturer_modules),
            "attempts": len(overall_attempts),
            "average_score": round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0.0,
        },
        "modules": report_modules,
    }


def flatten_student_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
    rows: list[dict[str, Any]] = []
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
    """Convert a list of dicts into CSV text."""
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def export_raw_csv(items: list[dict[str, Any]]) -> str:
    return export_rows_csv(items)


def export_payload(store: DataStore, kind: str, format_name: str, user: dict[str, Any] | None = None) -> tuple[str, str]:
    """Return file contents and a suggested filename."""
    kind = kind.lower()
    format_name = format_name.lower()

    if kind == "users":
        payload = get_list(store, "users")
    elif kind == "modules":
        payload = get_list(store, "modules")
    elif kind == "quizzes":
        payload = get_list(store, "quizzes")
    elif kind == "attempts":
        payload = get_list(store, "attempts")
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
