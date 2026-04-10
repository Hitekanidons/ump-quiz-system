
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const message = data && data.message ? data.message : "Something went wrong";
    throw new Error(message);
  }
  return data;
}

function getQuestionTypeTag(type) {
  const tags = {
    "multiple_choice": { label: "Multiple Choice", class: "q-type-multiple" },
    "true_false": { label: "True/False", class: "q-type-true-false" },
    "short_answer": { label: "Short Answer", class: "q-type-short" },
    "essay": { label: "Essay", class: "q-type-essay" }
  };
  const tag = tags[type] || tags["multiple_choice"];
  return `<span class="question-type-tag ${tag.class}">${tag.label}</span>`;
}

function renderQuestionForDisplay(question, quizId, isAnswered = false, userAnswer = null) {
  const type = question.type || "multiple_choice";
  let content = "";
  
  if (type === "multiple_choice") {
    content = question.options.map((opt, idx) => `
      <div class="option">
        <input type="radio" name="${quizId}_${question.id}" value="${idx}" ${isAnswered ? "disabled" : ""} ${userAnswer === idx ? "checked" : ""}>
        <label>${opt}</label>
      </div>
    `).join("");
    return `
      <div class="options-grid">
        ${content}
      </div>
    `;
  } else if (type === "true_false") {
    return `
      <div class="true-false-options">
        <div class="tf-option">
          <input type="radio" name="${quizId}_${question.id}" value="true" ${isAnswered ? "disabled" : ""} ${userAnswer === "true" ? "checked" : ""}>
          <label>True</label>
        </div>
        <div class="tf-option">
          <input type="radio" name="${quizId}_${question.id}" value="false" ${isAnswered ? "disabled" : ""} ${userAnswer === "false" ? "checked" : ""}>
          <label>False</label>
        </div>
      </div>
    `;
  } else if (type === "short_answer") {
    return `
      <input type="text" class="short-answer-input" placeholder="Type your answer here" name="${quizId}_${question.id}" value="${userAnswer || ""}" ${isAnswered ? "disabled" : ""}>
    `;
  } else if (type === "essay") {
    return `
      <textarea class="essay-textarea" placeholder="Write your essay answer here..." name="${quizId}_${question.id}" ${isAnswered ? "disabled" : ""}>${userAnswer || ""}</textarea>
    `;
  }
  return "";
}

function flash(message, kind = "ok") {
  const box = document.getElementById("flash");
  if (!box) return;
  box.className = `flash ${kind === "err" ? "err" : "ok"}`;
  box.textContent = message;
}

function tableFromRows(rows) {
  if (!rows || !rows.length) return "<p class='muted'>No records yet.</p>";
  const headers = Object.keys(rows[0]);
  const head = `<tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr>`;
  const body = rows.map(row => `<tr>${headers.map(h => `<td>${row[h] ?? ""}</td>`).join("")}</tr>`).join("");
  return `<table>${head}${body}</table>`;
}

function renderList(container, items, emptyText = "No records yet.") {
  const el = document.getElementById(container);
  if (!el) return;
  el.innerHTML = items && items.length ? items.map(item => item).join("") : `<p class="muted">${emptyText}</p>`;
}

function getFormData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function attachLogin() {
  const form = document.getElementById("loginForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/api/login", { method: "POST", body: JSON.stringify(getFormData(form)) });
      flash("Login successful. Redirecting...");
      setTimeout(() => window.location.href = "/", 350);
    } catch (err) {
      flash(err.message, "err");
    }
  });
}

function attachSignup() {
  const form = document.getElementById("signupForm");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const data = getFormData(form);
      await api("/api/signup", { method: "POST", body: JSON.stringify(data) });
      flash("Student account created. You can log in now.");
      form.reset();
    } catch (err) {
      flash(err.message, "err");
    }
  });
}

async function loadAdmin() {
  try {
    const summary = await api("/api/admin/summary");
    const summaryBox = document.getElementById("adminSummary");
    if (summaryBox) {
      const s = summary.summary;
      summaryBox.innerHTML = [
        ["Users", s.users],
        ["Lecturers", s.lecturers],
        ["Students", s.students],
        ["Modules", s.modules],
        ["Quizzes", s.quizzes],
        ["Attempts", s.attempts],
      ].map(([label, value]) => `<div class="stat"><span>${label}</span><strong>${value}</strong></div>`).join("");
    }

    const usersData = await api("/api/admin/users");
    const modulesData = await api("/api/admin/modules");

    const lecturers = usersData.users.filter(u => u.role === "lecturer");
    const students = usersData.users.filter(u => u.role === "student");

    document.getElementById("lecturerSelect").innerHTML =
      lecturers.map(u => `<option value="${u.id}">${u.full_name} (${u.username})</option>`).join("");
    document.getElementById("studentSelect").innerHTML =
      students.map(u => `<option value="${u.id}">${u.full_name} (${u.username})</option>`).join("");
    document.getElementById("moduleSelect").innerHTML =
      modulesData.modules.map(m => `<option value="${m.id}">${m.code} - ${m.name}</option>`).join("");

    document.getElementById("usersTable").innerHTML = tableFromRows(usersData.users.map(u => ({
      username: u.username,
      full_name: u.full_name,
      role: u.role,
      created_at: u.created_at
    })));

    const lecturersById = Object.fromEntries(usersData.users.map(u => [u.id, u]));
    document.getElementById("modulesTable").innerHTML = tableFromRows(modulesData.modules.map(m => ({
      code: m.code,
      name: m.name,
      lecturer: lecturersById[m.lecturer_id]?.full_name || "Unassigned",
      student_count: (m.student_ids || []).length
    })));
  } catch (err) {
    flash(err.message, "err");
  }

  const lecturerForm = document.getElementById("createLecturerForm");
  if (lecturerForm) {
    lecturerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/api/admin/users", { method: "POST", body: JSON.stringify({ ...getFormData(lecturerForm), role: "lecturer" }) });
        flash("Lecturer created.");
        location.reload();
      } catch (err) {
        flash(err.message, "err");
      }
    });
  }

  const moduleForm = document.getElementById("createModuleForm");
  if (moduleForm) {
    moduleForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/api/admin/modules", { method: "POST", body: JSON.stringify(getFormData(moduleForm)) });
        flash("Module created.");
        location.reload();
      } catch (err) {
        flash(err.message, "err");
      }
    });
  }

  const assignForm = document.getElementById("assignStudentForm");
  if (assignForm) {
    assignForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await api("/api/admin/assign-student", { method: "POST", body: JSON.stringify(getFormData(assignForm)) });
        flash("Student assigned.");
        location.reload();
      } catch (err) {
        flash(err.message, "err");
      }
    });
  }
}

function buildQuestionsFromForm(form) {
  const questionSlots = ["1", "2", "3"];
  const questions = [];
  for (const slot of questionSlots) {
    const text = form.querySelector(`[name="q${slot}_text"]`)?.value.trim();
    const qType = form.querySelector(`[name="q${slot}_type"]`)?.value || "multiple_choice";
    const points = form.querySelector(`[name="q${slot}_points"]`)?.value || "10";
    
    if (!text) continue;
    
    const question: any = {
      type: qType,
      text,
      points: Number(points || 1)
    };
    
    if (qType === "multiple_choice") {
      const optionsRaw = form.querySelector(`[name="q${slot}_options"]`)?.value.trim();
      const correctIndex = form.querySelector(`[name="q${slot}_correct"]`)?.value;
      const options = optionsRaw.split(",").map(x => x.trim()).filter(Boolean);
      question.options = options;
      question.correct_index = Number(correctIndex || 0);
    } else if (qType === "true_false") {
      const correctAnswer = form.querySelector(`[name="q${slot}_correct_tf"]`)?.value || "true";
      question.correct_answer = correctAnswer;
    } else if (qType === "short_answer") {
      const correctAnswers = form.querySelector(`[name="q${slot}_correct_sa"]`)?.value.trim();
      question.correct_answers = correctAnswers.split(",").map(x => x.trim()).filter(Boolean);
    } else if (qType === "essay") {
      const instructions = form.querySelector(`[name="q${slot}_instructions"]`)?.value.trim() || "";
      question.instructions = instructions;
    }
    
    questions.push(question);
  }
  return questions;
}

async function loadLecturer() {
  try {
    const modulesData = await api("/api/lecturer/modules");
    const modules = modulesData.modules || [];
    const moduleSelect = document.getElementById("quizModuleSelect");
    if (moduleSelect) {
      moduleSelect.innerHTML = modules.map(m => `<option value="${m.id}">${m.code} - ${m.name}</option>`).join("");
    }

    document.getElementById("lecturerModules").innerHTML = tableFromRows(modules.map(m => ({
      code: m.code,
      name: m.name,
      students: (m.student_ids || []).length,
      created_at: m.created_at
    })));

    if (modules.length) {
      const selectedModuleId = modules[0].id;
      const studentsData = await api(`/api/lecturer/modules/${selectedModuleId}/students`);
      const quizzesData = await api(`/api/lecturer/modules/${selectedModuleId}/quizzes`);
      document.getElementById("lecturerStudents").innerHTML = tableFromRows(studentsData.students.map(s => ({
        username: s.username,
        full_name: s.full_name,
        id: s.id
      })));
      document.getElementById("lecturerModules").innerHTML += `<p class="muted">Loaded module: ${modules[0].code}</p>`;
      document.getElementById("attemptsList").innerHTML = `<p class="muted">Use the API report below to see attempts by module.</p>`;
    }

    const reportData = await api("/api/lecturer/report");
    document.getElementById("lecturerReport").innerHTML = [
      `<p><strong>Modules:</strong> ${reportData.report.overall.modules}</p>`,
      `<p><strong>Attempts:</strong> ${reportData.report.overall.attempts}</p>`,
      `<p><strong>Average score:</strong> ${reportData.report.overall.average_score}</p>`,
      ...reportData.report.modules.map(module => `
        <div class="report-card">
          <h3>${module.code} - ${module.name}</h3>
          <p>Quizzes: ${module.quiz_count} | Students: ${module.student_count} | Attempts: ${module.attempt_count} | Avg: ${module.average_score}</p>
          ${tableFromRows(module.students)}
        </div>
      `)
    ].join("");

    const attemptsData = await api("/api/lecturer/attempts");
    document.getElementById("attemptsList").innerHTML = attemptsData.attempts.length ? attemptsData.attempts.sort((a, b) => {
      // Sort by status: pending_review first, then reviewed
      if (a.status === "pending_review" && b.status !== "pending_review") return -1;
      if (a.status !== "pending_review" && b.status === "pending_review") return 1;
      return 0;
    }).map(attempt => {
      const needsReview = attempt.status === "pending_review";
      const statusClass = needsReview ? "pending-review" : "reviewed";
      const statusLabel = needsReview ? "⚠️ Needs Review" : "✓ Reviewed";
      
      return `
        <div class="attempt-card" style="${needsReview ? "border-left: 4px solid var(--q-essay);" : ""}">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.8rem;">
            <div>
              <h4 style="margin: 0 0 0.3rem 0;">Attempt: ${attempt.id}</h4>
              <p class="muted" style="margin: 0; font-size: 0.85rem;">Quiz: ${attempt.quiz_id}</p>
              <p class="muted" style="margin: 0.3rem 0 0 0; font-size: 0.85rem;">Student: ${attempt.student_id}</p>
            </div>
            <span class="grade-status ${statusClass}">${statusLabel}</span>
          </div>
          
          <div class="attempt-summary" style="margin: 0.8rem 0;">
            <div class="summary-box">
              <span class="label">Auto Score</span>
              <span class="value">${attempt.auto_score} / ${attempt.total_score}</span>
            </div>
            <div class="summary-box">
              <span class="label">Current Grade</span>
              <span class="value" style="color: ${attempt.final_score >= (attempt.total_score / 2) ? 'var(--good)' : 'var(--bad)'};">${attempt.final_score}</span>
            </div>
            ${attempt.has_essay ? `<div class="summary-box" style="grid-column: 1 / -1; background: #fffbf0; border: 2px solid var(--q-essay); color: #92400e;"><strong>⚠️ Contains Essay Question(s)</strong></div>` : ""}
          </div>
          
          <form class="grade-form gradeForm" data-attempt="${attempt.id}">
            <label>
              Final Score (${attempt.total_score} max)
              <input type="number" min="0" max="${attempt.total_score}" name="score" value="${attempt.final_score}" required>
            </label>
            <label>
              Lecturer Comment
              <textarea name="comment" placeholder="Add feedback for the student" style="resize: vertical; min-height: 80px;">${attempt.lecturer_comment || ""}</textarea>
            </label>
            <button class="btn" type="submit">Save Grade</button>
          </form>
        </div>
      `;
    }).join("") : "<p class='muted'>No attempts yet.</p>";

    document.querySelectorAll(".gradeForm").forEach(form => {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const attemptId = form.dataset.attempt;
        try {
          const data = getFormData(form);
          await api(`/api/lecturer/attempts/${attemptId}/grade`, {
            method: "POST",
            body: JSON.stringify(data)
          });
          flash("Grade saved.");
          loadLecturer();
        } catch (err) {
          flash(err.message, "err");
        }
      });
    });

  } catch (err) {
    flash(err.message, "err");
  }

  const quizForm = document.getElementById("createQuizForm");
  if (quizForm) {
    quizForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const data = getFormData(quizForm);
        const questions = buildQuestionsFromForm(quizForm);
        await api("/api/lecturer/quizzes", {
          method: "POST",
          body: JSON.stringify({
            module_id: data.module_id,
            title: data.title,
            questions
          })
        });
        flash("Quiz created.");
        quizForm.reset();
        loadLecturer();
      } catch (err) {
        flash(err.message, "err");
      }
    });
  }
}

function renderStudentQuiz(quiz) {
  const answered = quiz.attempted && quiz.attempt ? true : false;
  const answerHtml = quiz.questions.map((q, idx) => {
    const userAnswer = quiz.attempt ? quiz.attempt.answers[q.id] : null;
    return `
      <div class="question-card ${q.type === "essay" ? "has-essay" : ""}">
        <div>
          <span class="q-number">${idx + 1}</span>
          ${getQuestionTypeTag(q.type)}
        </div>
        <h3>${q.text}</h3>
        <p class="muted" style="font-size: 0.9rem;">Points: <strong>${q.points}</strong></p>
        <div style="margin-top: 0.8rem;">
          ${renderQuestionForDisplay(q, quiz.id, answered, userAnswer)}
        </div>
      </div>
    `;
  }).join("");
  
  const totalPoints = quiz.questions.reduce((sum, q) => sum + q.points, 0);
  const scored = quiz.attempt ? `${quiz.attempt.final_score} / ${quiz.attempt.total_score}` : `0 / ${totalPoints}`;
  
  return `
    <div class="card wide">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <div>
          <h3 style="margin: 0 0 0.3rem 0;">${quiz.title}</h3>
          <p class="muted" style="margin: 0; font-size: 0.85rem;">Quiz ID: ${quiz.id}</p>
        </div>
        <div style="text-align: right;">
          ${answered ? `<span class="grade-status reviewed">Submitted</span>` : ""}
        </div>
      </div>
      ${answered ? `
        <div class="attempt-summary">
          <div class="summary-box">
            <span class="label">Your Score</span>
            <span class="value" style="color: ${quiz.attempt.final_score >= (quiz.attempt.total_score / 2) ? 'var(--good)' : 'var(--bad)'};">${scored}</span>
          </div>
          <div class="summary-box">
            <span class="label">Status</span>
            <span class="grade-status ${quiz.attempt.status === "pending_review" ? "pending-review" : "reviewed"}">${quiz.attempt.status === "pending_review" ? "Pending Review" : "Graded"}</span>
          </div>
          ${quiz.attempt.lecturer_comment ? `
          <div class="summary-box" style="grid-column: 1 / -1;">
            <span class="label">Lecturer's Comment</span>
            <p style="margin: 0.5rem 0 0 0; font-style: italic; color: var(--text);">"${quiz.attempt.lecturer_comment}"</p>
          </div>
          ` : ""}
        </div>
      ` : ""}
      <form class="studentQuizForm" data-quiz="${quiz.id}">
        ${answerHtml}
        ${answered ? "" : `<button class="btn" style="margin-top: 1rem;" type="submit">Submit Quiz</button>`}
      </form>
    </div>
  `;
}

async function loadStudent() {
  try {
    const modulesData = await api("/api/student/modules");
    document.getElementById("studentModules").innerHTML = tableFromRows(modulesData.modules.map(m => ({
      code: m.code,
      name: m.name,
      students: (m.student_ids || []).length,
    })));

    const quizzesData = await api("/api/student/quizzes");
    document.getElementById("studentQuizzes").innerHTML = quizzesData.quizzes.length
      ? quizzesData.quizzes.map(renderStudentQuiz).join("")
      : "<p class='muted'>No quizzes available.</p>";

    document.querySelectorAll(".studentQuizForm").forEach(form => {
      const quizId = form.dataset.quiz;
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const answers = {};
          
          // Collect radio button answers (multiple choice, true/false)
          const radioInputs = form.querySelectorAll("input[type='radio']:checked");
          radioInputs.forEach(input => {
            const [quizPrefix, qid] = input.name.split("_");
            answers[qid] = input.value;
          });
          
          // Collect text input answers (short answer)
          const textInputs = form.querySelectorAll("input[type='text'].short-answer-input");
          textInputs.forEach(input => {
            const [quizPrefix, qid] = input.name.split("_");
            answers[qid] = input.value;
          });
          
          // Collect textarea answers (essay)
          const textareas = form.querySelectorAll("textarea.essay-textarea");
          textareas.forEach(textarea => {
            const [quizPrefix, qid] = textarea.name.split("_");
            answers[qid] = textarea.value;
          });
          
          await api(`/api/student/quizzes/${quizId}/submit`, {
            method: "POST",
            body: JSON.stringify({ answers })
          });
          flash("Quiz submitted successfully!");
          loadStudent();
        } catch (err) {
          flash(err.message, "err");
        }
      });
    });

    const reportData = await api("/api/student/report");
    document.getElementById("studentReport").innerHTML = [
      `<p><strong>Attempts:</strong> ${reportData.report.overall.attempts}</p>`,
      `<p><strong>Average score:</strong> ${reportData.report.overall.average_score}</p>`,
      ...reportData.report.modules.map(module => `
        <div class="report-card">
          <h3>${module.code} - ${module.name}</h3>
          <p>Quizzes: ${module.quiz_count} | Attempts: ${module.attempt_count} | Avg: ${module.average_score}</p>
          ${tableFromRows(module.quizzes)}
        </div>
      `)
    ].join("");
  } catch (err) {
    flash(err.message, "err");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  if (window.PAGE === "login") attachLogin();
  if (window.PAGE === "signup") attachSignup();
  if (window.PAGE === "admin") loadAdmin();
  if (window.PAGE === "lecturer") loadLecturer();
  if (window.PAGE === "student") loadStudent();
});
