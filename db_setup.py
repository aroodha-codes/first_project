import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "college.db")

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Drop old tables ---
    cur.execute("DROP TABLE IF EXISTS timetable;")
    cur.execute("DROP TABLE IF EXISTS exams;")
    cur.execute("DROP TABLE IF EXISTS courses;")

    # --- Create tables ---
    cur.execute("""
    CREATE TABLE timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch TEXT,
        semester TEXT,
        section TEXT,
        day TEXT,
        time TEXT,
        subject TEXT,
        classroom TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch TEXT,
        semester TEXT,
        section TEXT,
        subject TEXT,
        date TEXT,
        time TEXT,
        classroom TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        branch TEXT,
        course_name TEXT,
        duration TEXT,
        fee TEXT
    );
    """)

    # --- Subjects for each branch ---
    branches = {
        "CSE": ["Data Structures", "Operating Systems", "DBMS", "Networks", "AI", "ML", "Cloud Computing", "Cyber Security"],
        "ECE": ["Digital Circuits", "Microprocessors", "Analog Communication", "Digital Communication", "VLSI", "Embedded Systems", "IoT", "Signal Processing"],
        "EEE": ["Basic Electrical Engg", "Power Systems", "Control Systems", "Machines", "Power Electronics", "Renewable Energy", "Smart Grids", "Instrumentation"],
        "CIVIL": ["Engineering Mechanics", "Surveying", "Fluid Mechanics", "Structural Analysis", "Geotechnical Engg", "Transportation Engg", "Environmental Engg", "Construction Management"],
        "ADE": ["Python Programming", "Data Mining", "AI Fundamentals", "ML Techniques", "Deep Learning", "Big Data", "NLP", "AI Ethics"]
    }

    # --- Timetable time slots ---
    time_slots = [
        "8:55 AM - 9:55 AM",
        "9:55 AM - 10:45 AM",
        "11:00 AM - 12:00 PM",
        "12:00 PM - 12:50 PM",
        "1:55 PM - 2:55 PM",
        "2:55 PM - 3:55 PM",
        "3:55 PM - 5:00 PM"
    ]

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    sections = ["A", "B"]

    timetable_data = []

    # Generate timetable dynamically
    for branch, subjects in branches.items():
        for sem in range(1, 9):
            for section in sections:
                for i, day in enumerate(days):
                    for j, slot in enumerate(time_slots):
                        subject = subjects[(sem + j + i) % len(subjects)]
                        timetable_data.append((
                            branch,
                            str(sem),
                            section,
                            day,
                            slot,
                            subject,
                            f"{branch[:2]}{sem}{section}{j+1}"
                        ))

    cur.executemany("""
        INSERT INTO timetable (branch, semester, section, day, time, subject, classroom)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, timetable_data)

    # --- Exams for all branches ---
    exam_data = []
    for branch, subjects in branches.items():
        for sem in range(1, 9):
            for section in sections:
                exam_data.append((branch, str(sem), section, subjects[sem-1], f"2025-12-{sem:02d}", "9:00 AM", f"{branch[:2]}{sem}{section}1"))

    cur.executemany("""
        INSERT INTO exams (branch, semester, section, subject, date, time, classroom)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, exam_data)

    # --- Courses ---
    course_data = [
        ("CSE", "Computer Science & Engineering", "4 Years", "₹80,000/year"),
        ("ECE", "Electronics & Communication Engg", "4 Years", "₹75,000/year"),
        ("EEE", "Electrical & Electronics Engg", "4 Years", "₹70,000/year"),
        ("CIVIL", "Civil Engineering", "4 Years", "₹65,000/year"),
        ("ADE", "Artificial Intelligence & Data Engg", "4 Years", "₹85,000/year")
    ]
    cur.executemany("""
        INSERT INTO courses (branch, course_name, duration, fee)
        VALUES (?, ?, ?, ?);
    """, course_data)

    conn.commit()
    conn.close()
    print("✅ Database created successfully with full-day timetable and all branches/semesters!")

if __name__ == "__main__":
    setup_database()

