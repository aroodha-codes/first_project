# app.py
import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, g, render_template, request, jsonify, redirect, url_for, session

APP_SECRET = "change_this_secret_in_prod"
ADMIN_USER = "admin"
ADMIN_PASS = "sdmit..in"
DB = os.path.join(os.path.dirname(__file__), "college.db")

app = Flask(__name__, template_folder="templates")
app.secret_key = APP_SECRET

# ---------------- DB Helpers ----------------
def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()

def parse_start_time(time_range: str) -> str:
    """
    Extract the start time and return as 'HH:MM' 24-hour for sorting.
    Accepts formats like '8:55 AM - 9:55 AM', '08:55 - 09:55', etc.
    """
    if not time_range:
        return "00:00"
    start = time_range.split("-")[0].strip()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%H.%M"):
        try:
            dt = datetime.strptime(start, fmt)
            return dt.strftime("%H:%M")
        except Exception:
            continue
    # fallback: try to replace AM/PM and parse
    try:
        cleaned = start.replace(".", ":").upper().replace("AM"," AM").replace("PM"," PM")
        dt = datetime.strptime(cleaned.strip(), "%I:%M %p")
        return dt.strftime("%H:%M")
    except Exception:
        return "00:00"

# ---------------- Auth ----------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin"))
        return f(*args, **kwargs)
    return wrapper

# ---------------- Public Pages & APIs ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/timetable")
def api_timetable():
    semester = request.args.get("semester", "1")
    db = get_db()
    rows = db.execute("""
        SELECT id, semester, day, time_range, start_time, subject, classroom
        FROM timetable
        WHERE semester=?
        ORDER BY 
            CASE day
                WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 WHEN 'Sunday' THEN 7 ELSE 8
            END,
            start_time
    """, (semester,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/exams")
def api_exams():
    semester = request.args.get("semester", "1")
    db = get_db()
    rows = db.execute("SELECT id, semester, subject, date, time, classroom FROM exams WHERE semester=? ORDER BY date, time", (semester,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/courses")
def api_courses():
    semester = request.args.get("semester", "1")
    db = get_db()
    rows = db.execute("SELECT id, semester, course_name, duration, fee FROM courses WHERE semester=? ORDER BY course_name", (semester,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/seating")
def api_seating():
    semester = request.args.get("semester", "1")
    db = get_db()
    rows = db.execute("SELECT id, semester, subject, student_name, usn, classroom, seat_number FROM exam_seating WHERE semester=? ORDER BY subject, classroom, seat_number", (semester,)).fetchall()
    return jsonify([dict(r) for r in rows])

# Chatbot route (returns HTML fragment in JSON)
@app.route("/get_answer", methods=["POST"])
def get_answer():
    data = request.get_json() or {}
    msg = (data.get("message","") or "").lower()
    semester = str(data.get("semester","1"))
    db = get_db()

    reply = "I can help with timetable, exams, courses, and seating. Try: 'timetable', 'exams', 'courses', 'seating'."

    if "timetable" in msg:
        rows = db.execute("SELECT day, time_range, start_time, subject, classroom FROM timetable WHERE semester=? ORDER BY day, start_time", (semester,)).fetchall()
        if rows:
            # group by day
            html = f"<h3>📅 Timetable — Semester {semester}</h3><table style='width:100%; border-collapse:collapse;'><tr style='background:#222;color:#fff;'><th style='padding:6px'>Day</th><th style='padding:6px'>Time</th><th style='padding:6px'>Subject</th><th style='padding:6px'>Room</th></tr>"
            current = None
            # convert rows to list of dict
            list_rows = [dict(r) for r in rows]
            # group
            from itertools import groupby
            for day, items in groupby(list_rows, key=lambda x: x['day']):
                items = list(items)
                first = True
                for it in items:
                    html += "<tr>"
                    if first:
                        html += f"<td style='padding:6px; vertical-align:top;' rowspan='{len(items)}'>{day}</td>"
                        first = False
                    html += f"<td style='padding:6px'>{it['time_range']}</td><td style='padding:6px'>{it['subject']}</td><td style='padding:6px'>{it['classroom']}</td></tr>"
            html += "</table>"
            reply = html
        else:
            reply = f"No timetable found for Semester {semester}."

    elif "exam" in msg or "exams" in msg:
        rows = db.execute("SELECT subject, date, time, classroom FROM exams WHERE semester=? ORDER BY date, time", (semester,)).fetchall()
        if rows:
            html = f"<h3>📝 Exams — Semester {semester}</h3><table style='width:100%; border-collapse:collapse;'><tr style='background:#222;color:#fff;'><th style='padding:6px'>Subject</th><th style='padding:6px'>Date</th><th style='padding:6px'>Time</th><th style='padding:6px'>Room</th></tr>"
            for r in rows:
                html += f"<tr><td style='padding:6px'>{r['subject']}</td><td style='padding:6px'>{r['date']}</td><td style='padding:6px'>{r['time']}</td><td style='padding:6px'>{r['classroom']}</td></tr>"
            html += "</table>"
            reply = html
        else:
            reply = f"No exams found for Semester {semester}."

    elif "course" in msg or "courses" in msg:
        rows = db.execute("SELECT course_name, duration, fee FROM courses WHERE semester=? ORDER BY course_name", (semester,)).fetchall()
        if rows:
            html = f"<h3>📚 Courses — Semester {semester}</h3><table style='width:100%; border-collapse:collapse;'><tr style='background:#222;color:#fff;'><th style='padding:6px'>Course</th><th style='padding:6px'>Duration</th><th style='padding:6px'>Fee</th></tr>"
            for r in rows:
                html += f"<tr><td style='padding:6px'>{r['course_name']}</td><td style='padding:6px'>{r['duration']}</td><td style='padding:6px'>{r['fee']}</td></tr>"
            html += "</table>"
            reply = html
        else:
            reply = "No course info."

    elif "seat" in msg or "seating" in msg:
        rows = db.execute("SELECT subject, student_name, usn, classroom, seat_number FROM exam_seating WHERE semester=? ORDER BY subject, classroom, seat_number", (semester,)).fetchall()
        if rows:
            html = f"<h3>💺 Exam Seating — Semester {semester}</h3><table style='width:100%; border-collapse:collapse;'><tr style='background:#222;color:#fff;'><th style='padding:6px'>Subject</th><th style='padding:6px'>Student</th><th style='padding:6px'>USN</th><th style='padding:6px'>Room</th><th style='padding:6px'>Seat</th></tr>"
            for r in rows:
                html += f"<tr><td style='padding:6px'>{r['subject']}</td><td style='padding:6px'>{r['student_name']}</td><td style='padding:6px'>{r['usn']}</td><td style='padding:6px'>{r['classroom']}</td><td style='padding:6px'>{r['seat_number']}</td></tr>"
            html += "</table>"
            reply = html
        else:
            reply = f"No seating found for Semester {semester}."

    return jsonify({"reply": reply})

# ---------------- Admin pages ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        u = request.form.get("username","")
        p = request.form.get("password","")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin_logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("admin.html", error="Invalid credentials")
    return render_template("admin.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

# ---------------- Admin APIs (manual only) ----------------
# TIMETABLE
@app.route("/admin/timetable/list")
@login_required
def admin_timetable_list():
    sem = request.args.get("semester","1")
    db = get_db()
    rows = db.execute("SELECT * FROM timetable WHERE semester=? ORDER BY day, start_time", (sem,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/admin/timetable/add", methods=["POST"])
@login_required
def admin_timetable_add():
    data = request.get_json() or {}
    sem = int(data.get("semester", 1))
    day = data.get("day","")
    time_range = data.get("time_range","")
    start_time = parse_start_time(time_range)
    subject = data.get("subject","")
    classroom = data.get("classroom","")
    db = get_db()
    db.execute("INSERT INTO timetable (semester, day, time_range, start_time, subject, classroom) VALUES (?, ?, ?, ?, ?, ?)",
               (sem, day, time_range, start_time, subject, classroom))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/timetable/update", methods=["POST"])
@login_required
def admin_timetable_update():
    data = request.get_json() or {}
    db = get_db()
    start_time = parse_start_time(data.get("time_range",""))
    db.execute("UPDATE timetable SET semester=?, day=?, time_range=?, start_time=?, subject=?, classroom=? WHERE id=?",
               (int(data.get("semester",1)), data.get("day"), data.get("time_range"), start_time, data.get("subject"), data.get("classroom"), data.get("id")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/timetable/delete", methods=["POST"])
@login_required
def admin_timetable_delete():
    data = request.get_json() or {}
    db = get_db()
    db.execute("DELETE FROM timetable WHERE id=?", (data.get("id"),))
    db.commit()
    return jsonify({"ok": True})

# EXAMS
@app.route("/admin/exams/list")
@login_required
def admin_exams_list():
    sem = request.args.get("semester","1")
    db = get_db()
    rows = db.execute("SELECT * FROM exams WHERE semester=? ORDER BY date, time", (sem,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/admin/exams/add", methods=["POST"])
@login_required
def admin_exams_add():
    data = request.get_json() or {}
    db = get_db()
    db.execute("INSERT INTO exams (semester, subject, date, time, classroom) VALUES (?, ?, ?, ?, ?)",
               (int(data.get("semester",1)), data.get("subject"), data.get("date"), data.get("time"), data.get("classroom")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/exams/update", methods=["POST"])
@login_required
def admin_exams_update():
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE exams SET semester=?, subject=?, date=?, time=?, classroom=? WHERE id=?",
               (int(data.get("semester",1)), data.get("subject"), data.get("date"), data.get("time"), data.get("classroom"), data.get("id")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/exams/delete", methods=["POST"])
@login_required
def admin_exams_delete():
    data = request.get_json() or {}
    db = get_db()
    db.execute("DELETE FROM exams WHERE id=?", (data.get("id"),))
    db.commit()
    return jsonify({"ok": True})

# COURSES
@app.route("/admin/courses/list")
@login_required
def admin_courses_list():
    sem = request.args.get("semester","1")
    db = get_db()
    rows = db.execute("SELECT * FROM courses WHERE semester=? ORDER BY course_name", (sem,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/admin/courses/add", methods=["POST"])
@login_required
def admin_courses_add():
    data = request.get_json() or {}
    db = get_db()
    db.execute("INSERT INTO courses (semester, course_name, duration, fee) VALUES (?, ?, ?, ?)",
               (int(data.get("semester",1)), data.get("course_name"), data.get("duration"), data.get("fee")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/courses/update", methods=["POST"])
@login_required
def admin_courses_update():
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE courses SET semester=?, course_name=?, duration=?, fee=? WHERE id=?",
               (int(data.get("semester",1)), data.get("course_name"), data.get("duration"), data.get("fee"), data.get("id")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/courses/delete", methods=["POST"])
@login_required
def admin_courses_delete():
    data = request.get_json() or {}
    db = get_db()
    db.execute("DELETE FROM courses WHERE id=?", (data.get("id"),))
    db.commit()
    return jsonify({"ok": True})

# SEATING
@app.route("/admin/seating/list")
@login_required
def admin_seating_list():
    sem = request.args.get("semester","1")
    db = get_db()
    rows = db.execute("SELECT * FROM exam_seating WHERE semester=? ORDER BY subject, classroom, seat_number", (sem,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/admin/seating/add", methods=["POST"])
@login_required
def admin_seating_add():
    data = request.get_json() or {}
    db = get_db()
    db.execute("INSERT INTO exam_seating (semester, subject, student_name, usn, classroom, seat_number) VALUES (?, ?, ?, ?, ?, ?)",
               (int(data.get("semester",1)), data.get("subject"), data.get("student_name"), data.get("usn"), data.get("classroom"), data.get("seat_number")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/seating/update", methods=["POST"])
@login_required
def admin_seating_update():
    data = request.get_json() or {}
    db = get_db()
    db.execute("UPDATE exam_seating SET semester=?, subject=?, student_name=?, usn=?, classroom=?, seat_number=? WHERE id=?",
               (int(data.get("semester",1)), data.get("subject"), data.get("student_name"), data.get("usn"), data.get("classroom"), data.get("seat_number"), data.get("id")))
    db.commit()
    return jsonify({"ok": True})

@app.route("/admin/seating/delete", methods=["POST"])
@login_required
def admin_seating_delete():
    data = request.get_json() or {}
    db = get_db()
    db.execute("DELETE FROM exam_seating WHERE id=?", (data.get("id"),))
    db.commit()
    return jsonify({"ok": True})

if __name__ == "__main__":
    if not os.path.exists(DB):
        print("Database not found. Run db_setup.py first.")
    app.run(host="0.0.0.0", port=5000, debug=True)
