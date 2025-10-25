# db_setup.py
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "college.db")

def setup():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Drop (safe for dev)
    c.executescript("""
    DROP TABLE IF EXISTS timetable;
    DROP TABLE IF EXISTS exams;
    DROP TABLE IF EXISTS courses;
    DROP TABLE IF EXISTS exam_seating;
    """)

    # Timetable with start_time (HH:MM) for sorting
    c.execute("""
    CREATE TABLE timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester INTEGER NOT NULL,
        day TEXT NOT NULL,
        time_range TEXT NOT NULL,
        start_time TEXT NOT NULL,    -- 'HH:MM' 24-hour for ordering
        subject TEXT NOT NULL,
        classroom TEXT NOT NULL
    );
    """)

    c.execute("""
    CREATE TABLE exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester INTEGER NOT NULL,
        subject TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        classroom TEXT NOT NULL
    );
    """)

    c.execute("""
    CREATE TABLE courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester INTEGER NOT NULL,
        course_name TEXT NOT NULL,
        duration TEXT,
        fee TEXT
    );
    """)

    c.execute("""
    CREATE TABLE exam_seating (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        semester INTEGER NOT NULL,
        subject TEXT NOT NULL,
        student_name TEXT NOT NULL,
        usn TEXT NOT NULL,
        classroom TEXT NOT NULL,
        seat_number TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    print("college.db created/updated.")

if __name__ == "__main__":
    setup()
