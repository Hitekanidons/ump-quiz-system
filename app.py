
"""Flask application for the online quiz system."""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, request, session, redirect, url_for, make_response

from auth import login_required, role_required
from storage import DataStore
from services import (
    authenticate,
    assign_lecturer_to_module,
    build_lecturer_report,
    build_student_report,
    create_module,
    create_quiz,
    create_user,
    enroll_student_in_module,
    export_payload,
    flatten_lecturer_report,
    flatten_student_report,
    get_attempts,
    get_module_by_id,
    get_public_modules,
    get_quiz_by_id,
    get_user_modules,
    grade_attempt,
    new_id,
    seed_demo_data,
    submit_quiz,
    get_list,
    find_by_id,
    save_list,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STORE = DataStore(DATA_DIR)

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-for-production"
app.config["JSON_SORT_KEYS"] = False

# Create starter records only the first time the app is launched.
seed_demo_data(STORE)


def current_user():
    return session.get("user")


def require_user_json():
    user = session.get("user")
    if not user:
        return None, (jsonify({"success": False, "message": "Login required"}), 401)
    return user, None


@app.route("/")
def home():
    if session.get("user"):
        role = session["user"].get("role")
        if role == "admin":
            return redirect(url_for("admin_dashboard"))
        if role == "lecturer":
            return redirect(url_for("lecturer_dashboard"))
        return redirect(url_for("student_dashboard"))
    return redirect(url_for("login_page"))


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/signup")
def signup_page():
    modules = get_public_modules(STORE)
    return render_template("signup.html", modules=modules)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():
    return render_template("admin_dashboard.html", user=current_user())


@app.route("/lecturer")
@login_required
@role_required("lecturer")
def lecturer_dashboard():
    return render_template("lecturer_dashboard.html", user=current_user())


@app.route("/student")
@login_required
@role_required("student")
def student_dashboard():
    return render_template("student_dashboard.html", user=current_user())


@app.get("/api/public/modules")
def api_public_modules():
    return jsonify({"success": True, "modules": get_public_modules(STORE)})


@app.post("/api/login")
def api_login():
    data = request.get_json(force=True, silent=True) or request.form or {}
    user = authenticate(STORE, data.get("username", ""), data.get("password", ""))
    if not user:
        return jsonify({"success": False, "message": "Invalid username or password"}), 401
    session["user_id"] = user["id"]
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }
    return jsonify({"success": True, "user": session["user"]})


@app.post("/api/signup")
def api_signup():
    data = request.get_json(force=True, silent=True) or {}
    try:
        username = data.get("username", "")
        password = data.get("password", "")
        full_name = data.get("full_name", "")
        module_id = data.get("module_id")

        if not username or not password or not full_name:
            raise ValueError("Username, password, and full name are required.")

        user = create_user(STORE, username, password, full_name, "student")
        if module_id:
            enroll_student_in_module(STORE, user["id"], module_id)

        return jsonify({"success": True, "message": "Student account created.", "user_id": user["id"]})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/me")
@login_required
def api_me():
    user = current_user()
    return jsonify({"success": True, "user": user})


@app.get("/api/admin/summary")
@login_required
@role_required("admin")
def api_admin_summary():
    users = get_list(STORE, "users")
    modules = get_list(STORE, "modules")
    quizzes = get_list(STORE, "quizzes")
    attempts = get_list(STORE, "attempts")
    return jsonify({
        "success": True,
        "summary": {
            "users": len(users),
            "lecturers": sum(1 for u in users if u.get("role") == "lecturer"),
            "students": sum(1 for u in users if u.get("role") == "student"),
            "modules": len(modules),
            "quizzes": len(quizzes),
            "attempts": len(attempts),
        }
    })


@app.get("/api/admin/users")
@login_required
@role_required("admin")
def api_admin_users():
    return jsonify({"success": True, "users": get_list(STORE, "users")})


@app.post("/api/admin/users")
@login_required
@role_required("admin")
def api_admin_create_user():
    data = request.get_json(force=True, silent=True) or {}
    try:
        user = create_user(
            STORE,
            data.get("username", ""),
            data.get("password", ""),
            data.get("full_name", ""),
            data.get("role", ""),
        )
        return jsonify({"success": True, "user": user})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/admin/modules")
@login_required
@role_required("admin")
def api_admin_modules():
    return jsonify({"success": True, "modules": get_list(STORE, "modules")})


@app.post("/api/admin/modules")
@login_required
@role_required("admin")
def api_admin_create_module():
    data = request.get_json(force=True, silent=True) or {}
    try:
        module = create_module(
            STORE,
            data.get("code", ""),
            data.get("name", ""),
            data.get("lecturer_id", ""),
        )
        return jsonify({"success": True, "module": module})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.post("/api/admin/assign-student")
@login_required
@role_required("admin")
def api_admin_assign_student():
    data = request.get_json(force=True, silent=True) or {}
    try:
        module = enroll_student_in_module(STORE, data.get("student_id", ""), data.get("module_id", ""))
        return jsonify({"success": True, "module": module})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.post("/api/admin/assign-lecturer")
@login_required
@role_required("admin")
def api_admin_assign_lecturer():
    data = request.get_json(force=True, silent=True) or {}
    try:
        module = assign_lecturer_to_module(STORE, data.get("module_id", ""), data.get("lecturer_id", ""))
        return jsonify({"success": True, "module": module})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/lecturer/modules")
@login_required
@role_required("lecturer")
def api_lecturer_modules():
    user = current_user()
    modules = get_user_modules(STORE, user)
    return jsonify({"success": True, "modules": modules})


@app.get("/api/lecturer/modules/<module_id>/students")
@login_required
@role_required("lecturer")
def api_lecturer_module_students(module_id):
    user = current_user()
    module = get_module_by_id(STORE, module_id)
    if not module or module.get("lecturer_id") != user["id"]:
        return jsonify({"success": False, "message": "Module not found."}), 404
    users = get_list(STORE, "users")
    students = [u for u in users if u.get("role") == "student" and u["id"] in module.get("student_ids", [])]
    return jsonify({"success": True, "students": students})


@app.get("/api/lecturer/modules/<module_id>/quizzes")
@login_required
@role_required("lecturer")
def api_lecturer_module_quizzes(module_id):
    user = current_user()
    module = get_module_by_id(STORE, module_id)
    quizzes = get_list(STORE, "quizzes")
    if not module or module.get("lecturer_id") != user["id"]:
        return jsonify({"success": False, "message": "Module not found."}), 404
    return jsonify({"success": True, "quizzes": [q for q in quizzes if q["module_id"] == module_id]})


@app.post("/api/lecturer/quizzes")
@login_required
@role_required("lecturer")
def api_lecturer_create_quiz():
    data = request.get_json(force=True, silent=True) or {}
    user = current_user()
    try:
        quiz = create_quiz(
            STORE,
            data.get("module_id", ""),
            data.get("title", ""),
            data.get("questions", []),
            user["id"],
        )
        return jsonify({"success": True, "quiz": quiz})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/lecturer/attempts")
@login_required
@role_required("lecturer")
def api_lecturer_attempts():
    user = current_user()
    modules = [m["id"] for m in get_user_modules(STORE, user)]
    quizzes = get_list(STORE, "quizzes")
    quiz_ids = {q["id"] for q in quizzes if q["module_id"] in modules}
    attempts = [a for a in get_attempts(STORE) if a["quiz_id"] in quiz_ids]
    return jsonify({"success": True, "attempts": attempts})


@app.post("/api/lecturer/attempts/<attempt_id>/grade")
@login_required
@role_required("lecturer")
def api_lecturer_grade_attempt(attempt_id):
    data = request.get_json(force=True, silent=True) or {}
    user = current_user()
    try:
        attempt = grade_attempt(
            STORE,
            user["id"],
            attempt_id,
            int(data.get("score", 0)),
            data.get("comment", ""),
        )
        return jsonify({"success": True, "attempt": attempt})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/lecturer/report")
@login_required
@role_required("lecturer")
def api_lecturer_report():
    user = current_user()
    report = build_lecturer_report(STORE, user["id"])
    return jsonify({"success": True, "report": report})


@app.get("/api/student/modules")
@login_required
@role_required("student")
def api_student_modules():
    user = current_user()
    return jsonify({"success": True, "modules": get_user_modules(STORE, user)})


@app.get("/api/student/quizzes")
@login_required
@role_required("student")
def api_student_quizzes():
    user = current_user()
    quizzes = get_list(STORE, "quizzes")
    attempts = get_attempts(STORE)
    modules = get_user_modules(STORE, user)
    module_ids = {m["id"] for m in modules}
    student_quizzes = [q for q in quizzes if q["module_id"] in module_ids]
    rows = []
    for quiz in student_quizzes:
        attempt = next((a for a in attempts if a["quiz_id"] == quiz["id"] and a["student_id"] == user["id"]), None)
        rows.append({
            **quiz,
            "attempted": bool(attempt),
            "attempt": attempt,
        })
    return jsonify({"success": True, "quizzes": rows})


@app.post("/api/student/quizzes/<quiz_id>/submit")
@login_required
@role_required("student")
def api_student_submit_quiz(quiz_id):
    user = current_user()
    data = request.get_json(force=True, silent=True) or {}
    try:
        attempt = submit_quiz(STORE, user["id"], quiz_id, data.get("answers", {}))
        return jsonify({"success": True, "attempt": attempt})
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/student/report")
@login_required
@role_required("student")
def api_student_report():
    user = current_user()
    report = build_student_report(STORE, user["id"])
    return jsonify({"success": True, "report": report})


@app.get("/api/export/<kind>")
@login_required
def api_export(kind: str):
    user = current_user()
    format_name = request.args.get("format", "json")
    try:
        content, filename = export_payload(STORE, kind, format_name, user=user)
        mimetype = "application/json" if format_name == "json" else "text/csv"
        response = make_response(content)
        response.headers["Content-Type"] = f"{mimetype}; charset=utf-8"
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400


@app.get("/api/debug/state")
@login_required
def api_debug_state():
    """Handy endpoint for quickly checking saved data during development."""
    return jsonify({
        "success": True,
        "users": get_list(STORE, "users"),
        "modules": get_list(STORE, "modules"),
        "quizzes": get_list(STORE, "quizzes"),
        "attempts": get_list(STORE, "attempts"),
    })


if __name__ == "__main__":
    app.run(debug=True)
