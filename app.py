from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, session
import mysql.connector
from reportlab.platypus import SimpleDocTemplate, Table
import os

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB CONNECTION ----------------
DB_HOST = os.environ.get("MYSQLHOST")
DB_USER = os.environ.get("MYSQLUSER")
DB_PASS = os.environ.get("MYSQLPASSWORD")
DB_NAME = os.environ.get("MYSQLDATABASE")
DB_PORT = os.environ.get("MYSQLPORT", 3306)




cursor = conn.cursor()

# ---------------- ROOT ----------------
@app.route('/')
def home():
    return redirect('/login')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        if user:
            session['user'] = username
            session['role'] = user[3]
            return redirect('/dashboard')
        else:
            return "Invalid login"

    return render_template('login.html')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    cursor.execute("SELECT COUNT(*) FROM student")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM department")
    total_depts = cursor.fetchone()[0]

    cursor.execute("SELECT IFNULL(ROUND(AVG(mark),2),0) FROM marks")
    avg_marks = cursor.fetchone()[0]

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_depts=total_depts,
        avg_marks=avg_marks
    )


# ---------------- ADD STUDENT ----------------
@app.route('/add', methods=['POST'])
def add_student():
    if 'user' not in session:
        return redirect('/login')

    name = request.form['name']
    age = request.form['age']
    dept_id = request.form['dept_id']
    year = request.form['year']

    cursor.execute("SELECT dept_name FROM department WHERE dept_id=%s", (dept_id,))
    dept = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM student
        WHERE dept_id=%s AND year=%s
    """, (dept_id, year))

    count = cursor.fetchone()[0] + 1
    reg_no = f"{str(year)[-2:]}{dept}{str(count).zfill(3)}"

    cursor.execute("""
        INSERT INTO student (name, age, dept_id, year, reg_no)
        VALUES (%s,%s,%s,%s,%s)
    """, (name, age, dept_id, year, reg_no))

    conn.commit()
    return redirect('/students')


# ---------------- STUDENTS ----------------
@app.route('/students')
def students():
    if 'user' not in session:
        return redirect('/login')

    cursor.execute("""
        SELECT s.student_id, s.name, s.age, d.dept_name, s.reg_no, s.year
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
    """)

    data = cursor.fetchall()

    cursor.execute("SELECT * FROM department")
    depts = cursor.fetchall()

    return render_template('students.html', students=data, depts=depts)


# ---------------- MARKS ----------------
@app.route('/marks', methods=['GET', 'POST'])
def marks():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        mark = request.form['mark']

        cursor.execute("""
            SELECT * FROM marks
            WHERE student_id=%s AND subject=%s
        """, (student_id, subject))

        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE marks
                SET mark=%s
                WHERE student_id=%s AND subject=%s
            """, (mark, student_id, subject))
        else:
            cursor.execute("""
                INSERT INTO marks (student_id, subject, mark)
                VALUES (%s,%s,%s)
            """, (student_id, subject, mark))

        conn.commit()
        return redirect('/marks')

    cursor.execute("SELECT student_id, name FROM student")
    students = cursor.fetchall()

    cursor.execute("""
        SELECT m.mark_id, s.name, m.subject, m.mark
        FROM marks m
        JOIN student s ON m.student_id = s.student_id
    """)

    marks_data = cursor.fetchall()

    return render_template('marks.html', students=students, marks=marks_data)


# ---------------- REPORT ----------------
@app.route('/report')
def report():
    if 'user' not in session:
        return redirect('/login')

    cursor.execute("""
        SELECT
            s.reg_no,
            s.name,

            MAX(CASE WHEN m.subject='CN' THEN m.mark END),
            MAX(CASE WHEN m.subject='DAA' THEN m.mark END),
            MAX(CASE WHEN m.subject='TOC' THEN m.mark END),
            MAX(CASE WHEN m.subject='WT' THEN m.mark END),
            MAX(CASE WHEN m.subject='DBMS' THEN m.mark END),

            IFNULL(SUM(m.mark),0),
            IFNULL(ROUND(AVG(m.mark),2),0)

        FROM student s
        LEFT JOIN marks m ON s.student_id = m.student_id
        GROUP BY s.student_id
        ORDER BY s.reg_no
    """)

    data = cursor.fetchall()
    return render_template('report.html', data=data)


# ---------------- DELETE ----------------
@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect('/login')

    if session.get('role') != 'admin':
        return "Access Denied"

    cursor.execute("DELETE FROM student WHERE student_id=%s", (id,))
    conn.commit()

    return redirect('/students')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))