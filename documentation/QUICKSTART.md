# Quick Start Guide - Auto-Grading Quiz System

## Setup & Running

### 1. Activate Virtual Environment
## Quick Start Commands

```bash
# Navigate to project based on where it is saved
cd "/Users/user/Downloads/python projects/quiz_system"

# create a virtual enviroment
# windows
 python -m venv myenv
# Activate virtual environment
 /myenv/bin/activate

 #install required packages from requirements.txt
 pip install -r requirements.text

# macos
python3 -m venv myenv 
# Activate virtual environment
source myenv/bin/activate



# Run the application
python3 app.py

# Visit http://127.0.0.1:5000/ on your browser
```

The application will start at `http://127.0.0.1:5000/`

### 3. Demo Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**Lecturer Account:**
- Username: `lecturer`
- Password: `lecturer123`

**Student Account:**
- Username: `student`
- Password: `student123`

---

## User Workflows

### For Lecturers

#### Create a Quiz with Different Question Types
1. Go to **Lecturer Dashboard**
2. Find **Create Quiz** section
3. Select a module from dropdown
4. Enter quiz title
5. **For each question:**
   - **Multiple Choice**: Click "Multiple Choice" button → Enter options separated by commas → Select correct option index
   - **True/False**: Click "True/False" button → Select "True" or "False" as correct answer
   - **Short Answer**: Click "Short Answer" button → Enter all possible correct answers (comma-separated, case-insensitive)
   - **Essay**: Click "Essay" button → Add optional instructions for students
   - Set points for each question
6. Click **Create Quiz**

#### Grade Student Submissions
1. Go to **Lecturer Dashboard**
2. Look at **"Attempts to Grade"** section
3. Submissions needing essay review appear first with warning
4. Review any essay answers provided by students
5. Adjust the score if needed (auto-score shown for reference)
6. Add feedback in the comment box
7. Click **Save Grade**

### For Students

#### Take a Quiz
1. Go to **Student Dashboard**
2. Find the quiz you want to take in **"Your quizzes"** section
3. Read each question with its type badge indicator
4. **Provide your answer:**
   - **Multiple Choice**: Select one option
   - **True/False**: Click True or False button
   - **Short Answer**: Type your answer
   - **Essay**: Write a detailed response
5. Click **Submit Quiz**
6. **Instant feedback!** Auto-graded questions show immediate results
7. If quiz has essays, status shows "Pending Review" until lecturer grades

#### View Your Grades
1. Go to **Student Dashboard**
2. Check **"Your report"** to see:
   - Overall attempts and average score
   - Per-module breakdown
   - Individual quiz scores and status
   - Lecturer comments (visible after grading)

---

## Key Features at a Glance

### Question Type Badges
-   MultipleChoice - Auto-graded
-   True/False - Auto-graded  
-   Short Answer - Auto-graded (exact match)
-   Essay - Requires manual grading

### Status Indicators
- ✓ **Graded**: Auto-graded and complete
-  **Pending Review**: Contains essay questions waiting for lecturer
- ✓ **Reviewed**: Lecturer has manually graded

### Score Display
- **Auto Score**: Points from auto-graded questions
- **Final Score**: After lecturer adjustments (if any)
- **Total Available**: Maximum possible points

---

## Example Quiz Creation

### Quiz: "Python Fundamentals"

**Question 1 (Multiple Choice, 10 points):**
- What is Python's most used package manager?
- Options: pip, npm, maven, gradle
- Correct: pip (index 0)

**Question 2 (True/False, 5 points):**
- Python is interpreted, not compiled
- Correct: True

**Question 3 (Short Answer, 5 points):**
- How do you create a list in Python?
- Acceptable answers: [], list()

**Question 4 (Essay, 10 points):**
- Explain the difference between lists and tuples
- No auto-grading; lecturer evaluates quality and awards 0-10 points

**Total: 30 points possible**

**If student answers Q1-3 correctly but Q4 pending:**
- Auto Score: 20/30
- Status: Pending Review (waiting on essay)
- Final Score: (After lecturer reviews and awards essay points)

---

## System Architecture Changes

### Backend Updates
- **services.py**: Added question type support and auto-grading logic
- **app.py**: Routes already support flexible question formats
- **data files**: Extended with type-specific fields

### Frontend Updates  
- **app.js**: Question rendering functions for each type
- **style.css**: Enhanced styling for question types and grading UI
- **Templates**: Updated lecturer dashboard with type selector

### Database Schema
- Questions now include `type` field
- Attempts track both `auto_score` and `final_score`
- New `has_essay` flag for pending review items

---

## Files Modified

1. **services.py** - Auto-grading logic and question type handling
2. **app.py** - Already compatible (no changes needed)
3. **static/js/app.js** - Question rendering and form handling
4. **static/css/style.css** - Enhanced styling for all question types
5. **templates/lecturer_dashboard.html** - Question type selector UI
6. **AUTO_GRADING_FEATURES.md** - Full feature documentation (this file)

---

## Common Questions

**Q: Can I edit a quiz after creation?**
A: Currently, quizzes are immutable. Create a new version if changes needed.

**Q: What if a student's short answer is close but not exact?**
A: Short answers must match exactly (case-insensitive). For fuzzy matching, use essays and grade manually.

**Q: How are exam marks distributed?**
A: You set points per question. Auto-graded = instant points. Essays = lecturer awards points.

**Q: Can students see their essay feedback?**
A: Yes! Once lecturer grades, comments appear in the student's quiz view.

**Q: What happens if there are no essay questions?**
A: Quiz auto-grades completely. Status shows "Graded" immediately.

---

## Tips for Best Results

1. **Use Multiple Choice** for objective factual questions → instant feedback
2. **Use Short Answer** for vocabulary or specific responses → auto-graded consistency
3. **Use True/False** for concept checks → quick scanning
4. **Use Essay** for critical thinking and deep understanding → lecturer evaluation
5. **Balance question types** for diverse assessment
6. **Set appropriate points** to reflect question difficulty
7. **Write clear short answer keys** with common variants

---

## Troubleshooting

**"Quiz didn't submit"**
- Ensure all questions are answered (required by default)
- Check browser console for error messages
- Try refreshing and resubmitting

**"Can't see essay feedback"**
- Lecturer hasn't graded yet (status may be "Pending Review")
- Ask lecturer to review - they'll see essay as top priority

**"Short answer not accepted"**
- Check spelling exactly (case-insensitive but spelling must match)
- Try one of the accepted answers listed in lecturer's quiz setup

**"Can't create quiz"**
- Ensure you're a lecturer assigned to the module
- At least one question must have text and required fields
- Check browser console for validation errors

---

Enjoy the enhanced auto-grading system! 🎓
