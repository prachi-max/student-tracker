from flask import Flask, render_template, request, redirect  , session, url_for
import sqlite3
from datetime import datetime
from xhtml2pdf import pisa
from io import BytesIO
from flask import make_response

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def init_db():
    conn = sqlite3.connect('student.db')
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            standard TEXT,
            subject TEXT,
            semester TEXT,
            topic TEXT,
            target_marks INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT,      
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'student' )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        date TEXT
    )''')

    conn.commit()
    conn.close()

                                                               # home


@app.route('/')
def home():
    return render_template('home.html')

                                                       #   sing up
@app.route('/SignUp', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']  # 'student' or 'parent'

        # Check if passwords match
        if password != confirm_password:
            return "Passwords do not match. Please try again."

        try:
            conn = sqlite3.connect('student.db')
            c = conn.cursor()
            c.execute('''
                INSERT INTO users (fullname, email, username, password, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (fullname, email, username, password, role))
            conn.commit()
            return redirect('/login')
        except sqlite3.IntegrityError:
            return " Username already exists."
        finally:
            conn.close()
    
    return render_template('SignUp.html')






@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('student.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[3]
            session['role'] = user[5]
            return redirect('/dashboard')
        else:
            return "Invalid credentials."
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

                                                            
                                                                        # app



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('student.db')
    c = conn.cursor()

    # If parent, show all data; else show only student's data
    if session['role'] == 'parent':
        c.execute("SELECT * FROM performance")
    else:
        c.execute("SELECT * FROM performance WHERE user_id=?", (session['user_id'],))

    data = c.fetchall()
    conn.close()

    # Process data for feedback and charts
    feedback = []
    subjects = []
    topics = []
    targets = []
    

    for row in data:
        standard = row[2]      # standard
        subject = row[3]       # subject
        semester = row[4]
        topic = row[5]
        target = row[6]        # target_marks

        feedback.append(generate_dummy_feedback(standard, subject, semester, topic, target))
        subjects.append(subject)
        topics.append(topic)
        targets.append(target)

    # Pass all needed variables to the dashboard template
    # return render_template('dashboard.html', data=data, feedback=feedback,
    #                        subjects=subjects, targets=targets)

        total_subjects = len(set(subjects))
        total_topics = len(set(topics))
        average_target = round(sum(targets) / len(targets), 2) if targets else 0

        return render_template('dashboard.html', data=data, feedback=feedback,
                           subjects=subjects, targets=targets,
                           total_subjects=total_subjects,
                           total_topics=total_topics,
                           average_target=average_target)


@app.route('/download')
def download_pdf():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('student.db')
    c = conn.cursor()

    if session['role'] == 'parent':
        c.execute("SELECT * FROM performance")
    else:
        c.execute("SELECT * FROM performance WHERE user_id=?", (session['user_id'],))
    data = c.fetchall()
    conn.close()

    html = render_template('report.html', data=data)
    result = BytesIO()
    pisa_status = pisa.CreatePDF(src=html, dest=result)

    if pisa_status.err:
        return "PDF generation failed"

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=student_report.pdf'
    return response



@app.route('/add', methods=['GET', 'POST'])
def add_data():
    if request.method == 'POST':
        form = request.form
        conn = sqlite3.connect('student.db')
        c = conn.cursor()
        c.execute('''INSERT INTO performance(user_id,  standard, subject, semester, topic,  target_marks)
                     VALUES (?, ?, ?, ?, ?, ?)''', 
                  (session['user_id'],form['standard'], form['subject'], form['semester'], form['topic'], form['target_marks']))
        conn.commit()
        conn.close()
        return redirect('/dashboard')
    return render_template('add_data.html')



@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    if request.method == 'POST':
        title = request.form['title']
        date = request.form['date']
        conn = sqlite3.connect('student.db')
        c = conn.cursor()
        c.execute("INSERT INTO calendar(user_id, title, date) VALUES (?, ?, ?)", (session['user_id'], title, date))
        conn.commit()
        conn.close()
    conn = sqlite3.connect('student.db')
    c = conn.cursor()
    c.execute("SELECT title, date FROM calendar WHERE user_id=?", (session['user_id'],))
    events = c.fetchall()
    conn.close()
    return render_template('calendar.html', events=events)



def generate_dummy_feedback(standard, subject, semester, topic, target_marks):
    standard = int(standard)
    if standard <= 5:
        return f"""
        📘 Revise basics of <b>{topic}</b> in <b>{subject}</b>.<br>
        🧠 Try drawing examples.<br>
        📺 Watch: <a href='https://www.youtube.com/results?search_query={topic}+for+kids'>YouTube Video</a><br>
        🎯 Tip: Practice with games and stories.
        """
    elif standard <= 10:
        return f"""
        📘 Practice MCQs on <b>{topic}</b>.<br>
        🛠️ Make a chart or short video.<br>
        📺 Watch: <a href='https://www.youtube.com/results?search_query={topic}+class+{standard}'>YouTube</a><br>
        🎯 Tip: Revise 30 mins daily.
        """
    else:
        return f"""
        📘 Solve board questions on <b>{topic}</b>.<br>
        🛠️ Build real project using it.<br>
        📺 Watch: <a href='https://www.youtube.com/results?search_query={topic}+for+class+{standard}'>Topic Video</a><br>
        🎯 Tip: Mock tests help reach {target_marks} marks.
      """



if __name__ == '__main__':
    init_db()
    app.run(debug=True , host='0.0.0.0', port=5000)
