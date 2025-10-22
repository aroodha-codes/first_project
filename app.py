from flask import Flask, request, jsonify, render_template, g
import sqlite3
import os
from typing import List, Tuple, Optional

app = Flask(__name__)
# Use an absolute path for the SQLite database so the app works
# no matter the current working directory.
DATABASE = os.path.join(app.root_path, "college.db")


# ---------- Database Helper ----------
def get_db():
    """Get a sqlite3 connection on the flask `g` context with row factory.

    Returns a connection where rows behave like tuples. The connection is
    created lazily and stored on `g` so it can be reused within a request.
    """
    if "db" not in g:
        # disable same-thread check because Flask may handle requests in
        # different threads in some setups (this is safe for a per-request
        # connection stored on `g`). Use a short timeout to reduce lock waits.
        conn = sqlite3.connect(DATABASE, check_same_thread=False, timeout=5)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def query_db(query: str, args: Tuple = (), one: bool = False) -> Optional[List[sqlite3.Row]]:
    """Run a query and return rows.

    - query: SQL query with ? placeholders
    - args: tuple/list of parameters
    - one: if True return a single row or None
    """
    conn = get_db()
    cur = conn.execute(query, args)
    try:
        rows = cur.fetchall()
    finally:
        # Explicitly close the cursor to release resources
        try:
            cur.close()
        except Exception:
            pass
    return (rows[0] if rows else None) if one else rows


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ---------- Home Page ----------
@app.route("/")
def home():
    return render_template("index.html")

# ---------- Chatbot API ----------
@app.route("/get_answer", methods=["POST"])
def get_answer():
    app.logger.info(f"Using database: {DATABASE}")
    try:
        if not request.is_json:
            return jsonify({"reply": "Please send a POST request with JSON data."}), 400

        data = request.get_json()
        user_query = (data.get("message", "") or "").lower()
        branch = data.get("branch", "")
        semester = data.get("semester", "")
        section = data.get("section", "")

        response = "Sorry, I can only answer about timetable, exams, or courses."

        # Timetable
        if "timetable" in user_query:
            if not branch or not semester or not section:
                return jsonify({"reply": "⚠️ Please select Branch, Semester, and Section first!"}), 400
            timetable = query_db(
                "SELECT day, time, subject, classroom FROM timetable WHERE branch=? AND semester=? AND section=? ORDER BY day, time",
                (branch, semester, section)
            )
            if timetable:
                # Create an HTML table
                response = f"<h3>📅 Timetable for {branch}-{semester}-{section}</h3>"
                response += """
                <table border='1' cellpadding='6' cellspacing='0' style='border-collapse: collapse; width:100%; text-align:left;'>
                  <tr style='background-color:#6c63ff; color:white;'>
                    <th>Day</th>
                    <th>Time</th>
                    <th>Subject</th>
                    <th>Classroom</th>
                  </tr>
                """
                for row in timetable:
                    response += f"""
                      <tr>
                        <td>{row['day']}</td>
                        <td>{row['time']}</td>
                        <td>{row['subject']}</td>
                        <td>{row['classroom']}</td>
                      </tr>
                    """
                response += "</table>"
            else:
                response = f"No timetable found for {branch}-{semester}-{section}."

        # Exams
        elif "exam" in user_query:
            if not branch or not semester or not section:
                return jsonify({"reply": "⚠️ Please select Branch, Semester, and Section first!"}), 400
            exams = query_db(
                "SELECT subject, date, time, classroom FROM exams WHERE branch=? AND semester=? AND section=?",
                (branch, semester, section)
            )
            if exams:
                response = f"Exam Schedule for {branch}-{semester}-{section}:\n"
                for row in exams:
                    response += f"{row['subject']} on {row['date']} at {row['time']} in Room {row['classroom']}\n"
            else:
                response = f"No exams found for {branch}-{semester}-{section}."

        # Courses & Fees
        elif "course" in user_query or "fee" in user_query:
            if not branch:
                return jsonify({"reply": "⚠️ Please select Branch first!"}), 400
            courses = query_db(
                "SELECT course_name, duration, fee FROM courses WHERE branch=?",
                (branch,)
            )
            if courses:
                response = f"Courses for {branch}:\n"
                for row in courses:
                    response += f"{row['course_name']} - Duration: {row['duration']}, Fee: {row['fee']}\n"
            else:
                response = f"No course details found for {branch}."

        return jsonify({"reply": response})

    except Exception as exc:
        # Log full exception on the server for debugging and return JSON error to client
        app.logger.exception("Unhandled error in /get_answer")
        # Return a JSON error message — this prevents the frontend getting an HTML error page
        return jsonify({
            "reply": "⚠️ Internal server error while processing your request.",
            "error": str(exc)
        }), 500

# ---------- Run App ----------
if __name__ == "__main__":
    # Use 0.0.0.0 so it's reachable from other devices on the network if needed.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
