# API Reference - Auto-Grading System

## Question Object Structure

### Multiple Choice Question
```json
{
  "id": "q_abc123",
  "type": "multiple_choice",
  "text": "What is 2+2?",
  "options": ["3", "4", "5", "6"],
  "correct_index": 1,
  "points": 10
}
```

### True/False Question
```json
{
  "id": "q_abc124",
  "type": "true_false",
  "text": "The Earth is flat",
  "correct_answer": "false",
  "points": 5
}
```

### Short Answer Question
```json
{
  "id": "q_abc125",
  "type": "short_answer",
  "text": "What is the capital of France?",
  "correct_answers": ["Paris", "paris", "PARIS"],
  "points": 5
}
```

### Essay Question
```json
{
  "id": "q_abc126",
  "type": "essay",
  "text": "Explain photosynthesis",
  "instructions": "Write 200-300 words describing the process",
  "points": 20
}
```

## Attempt Object Structure

### Auto-Graded Attempt (no essays)
```json
{
  "id": "attempt_xyz789",
  "quiz_id": "quiz_abc",
  "student_id": "u_student_1",
  "answers": {
    "q_abc123": 1,
    "q_abc124": "false",
    "q_abc125": "Paris"
  },
  "auto_score": 20,
  "final_score": 20,
  "total_score": 20,
  "status": "graded",
  "has_essay": false,
  "lecturer_comment": "",
  "graded_by": null,
  "submitted_at": "2026-04-10T13:10:44.583650+00:00"
}
```

### Pending Review Attempt (has essays)
```json
{
  "id": "attempt_xyz790",
  "quiz_id": "quiz_def",
  "student_id": "u_student_2",
  "answers": {
    "q_abc123": 1,
    "q_abc126": "Photosynthesis is the process where plants use sunlight..."
  },
  "auto_score": 10,
  "final_score": 0,
  "total_score": 30,
  "status": "pending_review",
  "has_essay": true,
  "lecturer_comment": "",
  "graded_by": null,
  "submitted_at": "2026-04-10T13:10:44.583650+00:00"
}
```

### Reviewed Attempt (lecturer graded)
```json
{
  "id": "attempt_xyz791",
  "quiz_id": "quiz_def",
  "student_id": "u_student_2",
  "answers": {
    "q_abc123": 1,
    "q_abc126": "Photosynthesis is the process..."
  },
  "auto_score": 10,
  "final_score": 28,
  "total_score": 30,
  "status": "reviewed",
  "has_essay": true,
  "lecturer_comment": "Excellent explanation! Minor grammar issues.",
  "graded_by": "u_lecturer_1",
  "submitted_at": "2026-04-10T13:10:44.583650+00:00"
}
```

## Endpoints

### Create Quiz
`POST /api/lecturer/quizzes`

**Request:**
```json
{
  "module_id": "m_prog101",
  "title": "Quiz Title",
  "questions": [
    {
      "type": "multiple_choice",
      "text": "Question text",
      "options": ["A", "B", "C"],
      "correct_index": 0,
      "points": 10
    },
    {
      "type": "essay",
      "text": "Essay question",
      "instructions": "Optional instructions",
      "points": 20
    }
  ]
}
```

**Response (201):**
```json
{
  "success": true,
  "quiz": { ...full quiz object... }
}
```

---

### Submit Quiz
`POST /api/student/quizzes/<quiz_id>/submit`

**Request:**
```json
{
  "answers": {
    "q_abc123": 1,
    "q_abc124": "true",
    "q_abc125": "Paris",
    "q_abc126": "My essay response here..."
  }
}
```

**Response (200):**
```json
{
  "success": true,
  "attempt": {
    "id": "attempt_xyz",
    "status": "graded|pending_review",
    "auto_score": 20,
    "final_score": 20,
    "total_score": 50,
    "has_essay": false
  }
}
```

**Answer Format by Question Type:**
- Multiple Choice: `"q_id": 0` (option index as number)
- True/False: `"q_id": "true"` (string "true" or "false")
- Short Answer: `"q_id": "answer text"` (string - case insensitive)
- Essay: `"q_id": "full essay text"` (string)

---

### Get Student Quizzes
`GET /api/student/quizzes`

**Response (200):**
```json
{
  "success": true,
  "quizzes": [
    {
      "id": "quiz_1",
      "module_id": "m_1",
      "title": "Quiz Title",
      "questions": [...],
      "created_by": "u_lecturer_1",
      "published": true,
      "attempted": false,
      "attempt": null
    },
    {
      "id": "quiz_2",
      "module_id": "m_1",
      "title": "Quiz 2",
      "questions": [...],
      "attempted": true,
      "attempt": {
        "id": "attempt_xyz",
        "status": "pending_review",
        "final_score": 15,
        "total_score": 30,
        "has_essay": true
      }
    }
  ]
}
```

---

### Get Lecturer Attempts (to grade)
`GET /api/lecturer/attempts`

**Response (200):**
```json
{
  "success": true,
  "attempts": [
    {
      "id": "attempt_xyz",
      "quiz_id": "quiz_2",
      "student_id": "u_student_1",
      "answers": { ...submitted answers... },
      "auto_score": 10,
      "final_score": 10,
      "total_score": 30,
      "status": "pending_review",
      "has_essay": true,
      "lecturer_comment": "",
      "graded_by": null,
      "submitted_at": "2026-04-10T13:10:44.583650+00:00"
    }
  ]
}
```

**Note:** Returns all attempts regardless of status. Frontend should sort by `status === "pending_review"` to prioritize essays.

---

### Grade Attempt
`POST /api/lecturer/attempts/<attempt_id>/grade`

**Request:**
```json
{
  "score": 28,
  "comment": "Great essay! You explained the concept well."
}
```

**Response (200):**
```json
{
  "success": true,
  "attempt": {
    "id": "attempt_xyz",
    "status": "reviewed",
    "auto_score": 10,
    "final_score": 28,
    "total_score": 30,
    "has_essay": true,
    "lecturer_comment": "Great essay! You explained the concept well.",
    "graded_by": "u_lecturer_1"
  }
}
```

**Validation:**
- Score must be 0-total_score
- Total score calculated from all questions
- Auto score cannot be changed (read-only)
- Final score = lecturer's awarded points (including auto_score bonus)

---

### Get Student Report
`GET /api/student/report`

**Response (200):**
```json
{
  "success": true,
  "report": {
    "student": {
      "id": "u_student_1",
      "username": "student",
      "full_name": "Demo Student"
    },
    "overall": {
      "attempts": 5,
      "average_score": 75.5
    },
    "modules": [
      {
        "module_id": "m_1",
        "code": "PROG101",
        "name": "Introduction to Programming",
        "quiz_count": 3,
        "attempt_count": 2,
        "average_score": 80.0,
        "quizzes": [
          {
            "quiz_id": "quiz_1",
            "title": "Quiz 1",
            "status": "attempted",
            "score": 85,
            "total_score": 100,
            "submitted_at": "2026-04-10T13:10:44.583650+00:00"
          }
        ]
      }
    ]
  }
}
```

---

### Get Lecturer Report
`GET /api/lecturer/report`

**Response (200):**
```json
{
  "success": true,
  "report": {
    "lecturer": {
      "id": "u_lecturer_1",
      "username": "lecturer",
      "full_name": "Demo Lecturer"
    },
    "overall": {
      "modules": 2,
      "attempts": 15,
      "average_score": 78.2
    },
    "modules": [
      {
        "module_id": "m_1",
        "code": "PROG101",
        "name": "Introduction to Programming",
        "quiz_count": 3,
        "student_count": 5,
        "attempt_count": 8,
        "average_score": 82.5,
        "students": [
          {
            "student_id": "u_student_1",
            "username": "student1",
            "full_name": "Student One",
            "attempt_count": 2,
            "average_score": 85.0
          }
        ]
      }
    ]
  }
}
```

---

## Auto-Grading Logic

### Question Type Grading

#### Multiple Choice
```
Input: student selected index
Process: index === correct_index
Output: points if match, 0 if no match
```

#### True/False
```
Input: "true" or "false"
Process: string === correct_answer
Output: points if match, 0 if no match
```

#### Short Answer
```
Input: student text (any case/whitespace)
Process: text.lower().strip() IN correct_answers
Output: points if match, 0 if no match
Note: Case-insensitive matching
```

#### Essay
```
Input: full text response
Process: stored, NOT graded
Output: 0 (awaits lecturer grading)
Attempt Status: marked "pending_review"
```

### Overall Attempt Scoring
```
auto_score = sum of auto-graded question scores
has_essay = any question type is essay
status = "pending_review" if has_essay, else "graded"
final_score = auto_score (initially)
After lecturer grades: final_score = lecturer's awarded total
```

---

## Error Responses

### 400 Bad Request
```json
{
  "success": false,
  "message": "Quiz not found"
}
```

Possible messages:
- "Student not found"
- "Quiz not found"
- "You are not enrolled in this module"
- "You have already submitted this quiz"
- "Question must have text and at least 2 options"
- "Score must be within the valid range"

### 401 Unauthorized
```json
{
  "success": false,
  "message": "Login required"
}
```

### 403 Forbidden
```json
{
  "success": false,
  "message": "You can only grade quizzes in your own module"
}
```

---

## Data Persistence

All data stored in JSON files:
- `data/users.json` - User accounts and credentials
- `data/modules.json` - Course modules
- `data/quizzes.json` - Quiz definitions (with questions)
- `data/attempts.json` - Student submission attempts (with answers)

No database migration needed - system auto-detects question types by presence of type field.

---

## Example Workflow

### 1. Lecturer Creates Quiz
```bash
curl -X POST http://localhost:5000/api/lecturer/quizzes \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": "m_1",
    "title": "Python Fundamentals",
    "questions": [
      {"type": "multiple_choice", "text": "What is 2+2?", "options": ["3", "4", "5"], "correct_index": 1, "points": 10},
      {"type": "true_false", "text": "Python is object-oriented", "correct_answer": "true", "points": 5},
      {"type": "essay", "text": "Explain loops", "points": 15}
    ]
  }'
```

### 2. Student Submits Quiz
```bash
curl -X POST http://localhost:5000/api/student/quizzes/quiz_1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "answers": {
      "q_1": 1,
      "q_2": "true",
      "q_3": "Loops iterate through sequences..."
    }
  }'
```

Response: `status: "pending_review"` (has essay)

### 3. Lecturer Grades
```bash
curl -X POST http://localhost:5000/api/lecturer/attempts/attempt_1/grade \
  -H "Content-Type: application/json" \
  -d '{
    "score": 28,
    "comment": "Excellent explanation of loops!"
  }'
```

Response: `status: "reviewed"`, `final_score: 28`

### 4. Student Checks Report
```bash
curl http://localhost:5000/api/student/report
```

Shows attempt with final_score: 28, status: "reviewed", lecturer comment visible.

---

## Compatibility Notes

- Existing quizzes with `type` field missing default to `multiple_choice`
- Old attempts with `status: "graded"` remain valid
- All new attempts follow new schema
- System handles mixed quiz formats seamlessly

---

## Rate Limiting & Performance

- No built-in rate limiting (for classroom use)
- JSON file I/O adequate for ~100 students per module
- Consider database migration for 1000+ users
- Grading operations are synchronous (completes in <100ms)

---

For more details: See AUTO_GRADING_FEATURES.md and QUICKSTART.md
