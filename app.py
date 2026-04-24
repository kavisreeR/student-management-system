from flask import Flask, render_template, request, redirect, session, jsonify
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB CONNECTION ----------------
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="K2007",
    database="student_db",
    port=3306
)

cursor = conn.cursor()

# ---------------- HOME ----------------
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
    students = cursor.fetchall()

    cursor.execute("SELECT * FROM department")
    depts = cursor.fetchall()

    return render_template('students.html', students=students, depts=depts)

# ---------------- LIVE SEARCH ----------------
@app.route('/search_ajax')
def search_ajax():
    name = request.args.get('name', '')

    cursor.execute("""
        SELECT s.student_id, s.name, s.age, d.dept_name, s.reg_no, s.year
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
        WHERE s.name LIKE %s
    """, ('%' + name + '%',))

    data = cursor.fetchall()

    result = []
    for row in data:
        result.append({
            "id": row[0],
            "name": row[1],
            "age": row[2],
            "dept": row[3],
            "reg_no": row[4],
            "year": row[5]
        })

    return jsonify(result)

# ---------------- FILTER ----------------
@app.route('/filter')
def filter_students():
    dept_id = request.args.get('dept_id')

    cursor.execute("""
        SELECT s.student_id, s.name, s.age, d.dept_name, s.reg_no, s.year
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
        WHERE s.dept_id=%s
    """, (dept_id,))

    students = cursor.fetchall()

    cursor.execute("SELECT * FROM department")
    depts = cursor.fetchall()

    return render_template('students.html', students=students, depts=depts)

# ---------------- ADD STUDENT ----------------
@app.route('/add', methods=['POST'])
def add_student():
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

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>')
def delete(id):
    cursor.execute("DELETE FROM student WHERE student_id=%s", (id,))
    conn.commit()
    return redirect('/students')

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

# ---------------- EDIT MARK ----------------
@app.route('/edit_mark/<int:id>', methods=['GET', 'POST'])
def edit_mark(id):
    if request.method == 'POST':
        mark = request.form['mark']

        cursor.execute("""
            UPDATE marks SET mark=%s WHERE mark_id=%s
        """, (mark, id))
        conn.commit()

        return redirect('/marks')

    cursor.execute("""
        SELECT m.mark_id, s.name, m.subject, m.mark
        FROM marks m
        JOIN student s ON m.student_id = s.student_id
        WHERE m.mark_id=%s
    """, (id,))

    mark = cursor.fetchone()

    return render_template('edit_mark.html', mark=mark)

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
    """)

    data = cursor.fetchall()
    return render_template('report.html', data=data)

@app.route('/analytics')
def analytics():
    if 'user' not in session:
        return redirect('/login')

    # chart
    cursor.execute("""
        SELECT subject, AVG(mark)
        FROM marks
        GROUP BY subject
    """)
    chart_data = cursor.fetchall()

    subjects = [row[0] for row in chart_data]
    marks = [float(row[1]) for row in chart_data]

    # TOPPERS (FIXED)
    cursor.execute("""
        SELECT m.subject, s.name, m.mark
        FROM marks m
        JOIN student s ON m.student_id = s.student_id
        WHERE (m.subject, m.mark) IN (
            SELECT subject, MAX(mark)
            FROM marks
            GROUP BY subject
        )
    """)
    toppers = cursor.fetchall()

    # dept ranking
    cursor.execute("""
        SELECT d.dept_name, ROUND(AVG(m.mark),2)
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
        JOIN marks m ON s.student_id = m.student_id
        GROUP BY d.dept_name
    """)
    dept_rank = cursor.fetchall()

    return render_template(
        "analytics.html",
        subjects=subjects,
        marks=marks,
        toppers=toppers,
        dept_rank=dept_rank
    )

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)