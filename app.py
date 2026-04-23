from flask import Flask, render_template, request, redirect, session
from reportlab.platypus import SimpleDocTemplate, Table
import mysql.connector

app = Flask(__name__)
app.secret_key = "secret123"

# DB connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="K2007",   # 👈 change this
    database="student_db"
)

cursor = conn.cursor()

# 🔹 Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        # 🔥 ADD HERE
        if user:
            session['user'] = username
            session['role'] = user[3]   # role column (admin/staff)
            return redirect('/dashboard')
        else:
            return "Invalid login"

    return render_template('login.html')


# 🔹 Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    # total students
    cursor.execute("SELECT COUNT(*) FROM student")
    total_students = cursor.fetchone()[0]

    # total departments
    cursor.execute("SELECT COUNT(*) FROM department")
    total_depts = cursor.fetchone()[0]

    # average marks
    cursor.execute("SELECT ROUND(AVG(mark),2) FROM marks")
    avg_marks = cursor.fetchone()[0]

    return render_template(
        'dashboard.html',
        total_students=total_students,
        total_depts=total_depts,
        avg_marks=avg_marks
    )

# 🔹 Add student
@app.route('/add', methods=['POST'])
def add_student():
    if 'user' not in session:
        return redirect('/')

    name = request.form['name']
    age = request.form['age']
    dept_id = request.form['dept_id']
    year = request.form['year']

    # dept name (CSE, ECE...)
    cursor.execute("SELECT dept_name FROM department WHERE dept_id=%s", (dept_id,))
    dept = cursor.fetchone()[0]

    # count students in same dept + year
    cursor.execute("""
        SELECT COUNT(*) FROM student 
        WHERE dept_id=%s AND year=%s
    """, (dept_id, year))

    count = cursor.fetchone()[0] + 1

    # generate reg no (23CSE001)
    reg_no = f"{str(year)[-2:]}{dept}{str(count).zfill(3)}"

    cursor.execute("""
        INSERT INTO student (name, age, dept_id, year, reg_no)
        VALUES (%s,%s,%s,%s,%s)
    """, (name, age, dept_id, year, reg_no))

    conn.commit()

    return redirect('/students')

# 🔹 View students
@app.route('/students')

def students():
    if 'user' not in session:
        return redirect('/')

    cursor.execute("""
        SELECT s.student_id, s.name, s.age, d.dept_name, s.reg_no, s.year
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM department")
    depts = cursor.fetchall()

    return render_template('students.html', students=data, depts=depts)

@app.route('/analytics')
def analytics():
    if 'user' not in session:
        return redirect('/')

    # 🔥 SUBJECT TOPPERS
    cursor.execute("""
        SELECT subject, s.name, MAX(mark)
        FROM marks m
        JOIN student s ON m.student_id = s.student_id
        GROUP BY subject
    """)
    toppers = cursor.fetchall()

    # 🔥 DEPARTMENT RANKING (by avg marks)
    cursor.execute("""
        SELECT d.dept_name, ROUND(AVG(m.mark),2) as avg_mark
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
        JOIN marks m ON s.student_id = m.student_id
        GROUP BY d.dept_id
        ORDER BY avg_mark DESC
    """)
    dept_rank = cursor.fetchall()

    # 🔥 CHART DATA (subject avg)
    cursor.execute("""
        SELECT subject, AVG(mark)
        FROM marks
        GROUP BY subject
    """)
    chart_data = cursor.fetchall()

    subjects = [c[0] for c in chart_data]
    marks = [float(c[1]) for c in chart_data]

    return render_template(
        'analytics.html',
        toppers=toppers,
        dept_rank=dept_rank,
        subjects=subjects,
        marks=marks
    )

# 🔹 Edit student
@app.route('/edit_mark/<int:id>', methods=['GET', 'POST'])
def edit_mark(id):
    if 'user' not in session:
        return redirect('/')

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
    
    data = cursor.fetchone()

    return render_template('edit_mark.html', mark=data)

@app.route('/search')
def search():
    if 'user' not in session:
        return redirect('/')

    name = request.args.get('name')

    cursor.execute("""
    SELECT s.student_id, s.name, s.age, d.dept_name
    FROM student s
    JOIN department d ON s.dept_id = d.dept_id
    WHERE s.name LIKE %s
    """, ('%' + name + '%',))

    data = cursor.fetchall()
    cursor.execute("SELECT * FROM department")
    depts = cursor.fetchall()

    return render_template('students.html', students=data, depts=depts)

@app.route('/filter')
def filter():
    if 'user' not in session:
        return redirect('/')

    dept_id = request.args.get('dept_id')

    cursor.execute("""
    SELECT s.student_id, s.name, s.age, d.dept_name
    FROM student s
    JOIN department d ON s.dept_id = d.dept_id
    WHERE s.dept_id = %s
    """, (dept_id,))

    data = cursor.fetchall()
    cursor.execute("SELECT * FROM department")
    depts = cursor.fetchall()
    return render_template('students.html', students=data,depts=depts)


@app.route('/report')
def report():
    if 'user' not in session:
        return redirect('/')

    cursor.execute("""
    SELECT 
        s.reg_no,
        s.name,

        MAX(CASE WHEN m.subject='CN' THEN m.mark END),
        MAX(CASE WHEN m.subject='DAA' THEN m.mark END),
        MAX(CASE WHEN m.subject='TOC' THEN m.mark END),
        MAX(CASE WHEN m.subject='WT' THEN m.mark END),
        MAX(CASE WHEN m.subject='DBMS' THEN m.mark END),

        SUM(m.mark),
        ROUND(AVG(m.mark),2)

    FROM student s
    LEFT JOIN marks m ON s.student_id = m.student_id
    GROUP BY s.student_id
    ORDER BY s.reg_no
    """)

    data = cursor.fetchall()

    return render_template('report.html', data=data)

@app.route('/marks', methods=['GET', 'POST'])
def marks():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        student_id = request.form['student_id']
        subject = request.form['subject']
        mark = request.form['mark']

        # 🔥 check if already exists
        cursor.execute("""
            SELECT * FROM marks 
            WHERE student_id=%s AND subject=%s
        """, (student_id, subject))

        existing = cursor.fetchone()

        if existing:
            # 🔥 UPDATE instead of insert
            cursor.execute("""
                UPDATE marks 
                SET mark=%s 
                WHERE student_id=%s AND subject=%s
            """, (mark, student_id, subject))
        else:
            # 🔥 INSERT new
            cursor.execute("""
                INSERT INTO marks (student_id, subject, mark)
                VALUES (%s,%s,%s)
            """, (student_id, subject, mark))

        conn.commit()

        return redirect('/marks')

    # 🔥 dropdown students
    cursor.execute("SELECT student_id, name FROM student")
    students = cursor.fetchall()

    # 🔥 table data
    cursor.execute("""
        SELECT m.mark_id, s.name, m.subject, m.mark
        FROM marks m
        JOIN student s ON m.student_id = s.student_id
    """)
    marks_data = cursor.fetchall()

    return render_template('marks.html', students=students, marks=marks_data)

@app.route('/delete/<int:id>')
def delete(id):
    if 'user' not in session:
        return redirect('/')

    if session.get('role') != 'admin':
        return "Access Denied"

    cursor.execute("DELETE FROM student WHERE student_id=%s", (id,))
    conn.commit()

    return redirect('/students')

@app.route('/chart')
def chart():
    if 'user' not in session:
        return redirect('/')

    cursor.execute("""
        SELECT subject, AVG(mark)
        FROM marks
        GROUP BY subject
    """)
    data = cursor.fetchall()

    subjects = [d[0] for d in data]
    marks = [float(d[1]) for d in data]

    return render_template('chart.html', subjects=subjects, marks=marks)

@app.route('/search_ajax')
def search_ajax():
    name = request.args.get('name')

    cursor.execute("""
        SELECT s.student_id, s.name, s.age, d.dept_name, s.reg_no, s.year
        FROM student s
        JOIN department d ON s.dept_id = d.dept_id
        WHERE s.name LIKE %s
    """, ('%' + name + '%',))

    return {'data': cursor.fetchall()}

@app.route('/download_report')
def download_report():
    cursor.execute("""
        SELECT s.name, AVG(m.mark)
        FROM student s
        JOIN marks m ON s.student_id = m.student_id
        GROUP BY s.student_id
    """)
    data = cursor.fetchall()

    pdf = SimpleDocTemplate("report.pdf")
    table = Table([["Name", "Average"]] + list(data))
    pdf.build([table])

    return "PDF Generated (check project folder)"

# 🔹 Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


# 🔹 Run
if __name__ == '__main__':
    app.run(debug=True)