from flask import Flask, render_template, redirect, url_for, request, flash, session, Response
import os
import sqlite3
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import csv
from flask import request
import random
import string
from flask import g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('db/library.db')
        g.db.row_factory = sqlite3.Row
    return g.db



def generate_username(name):
    return name.lower().replace(" ", "") + str(random.randint(100, 999))

def generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


app = Flask(__name__)
app.secret_key = 'balaji_secret_key_123'

DB_PATH = os.path.join('db', 'library.db')

def get_students():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
    return students

def get_total_seats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS settings (total_seats INTEGER DEFAULT 60)")
    cur.execute("SELECT total_seats FROM settings LIMIT 1")
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO settings (total_seats) VALUES (60)")
        conn.commit()
        total_seats = 60
    else:
        total_seats = row[0]
    conn.close()
    return total_seats



def get_settings():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Yeh dict jaise access dene ke liye
    cur = conn.cursor()
    cur.execute("SELECT * FROM settings")
    row = cur.fetchone()  # Pehla row milega (humare case me ek hi row hoti hai)
    conn.close()
    return row

def update_settings_table_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("ALTER TABLE settings ADD COLUMN library_name TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN library_address TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN library_phone TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN opening_hours TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN about TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()



@app.route('/')
def index():
    students = get_students()
    total_students = len(students)
    active_students = sum(1 for s in students if s['status'] == 'active')
    total_seats = get_total_seats()
    empty_seats = total_seats - active_students

    # ✅ Fetch authorities also
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM authorities")
    members = cur.fetchall()
    conn.close()

    return render_template('index.html', title="Home", 
                           total_students=total_students,
                           active_students=active_students,
                           total_seats=total_seats,
                           empty_seats=empty_seats,
                           members=members)  # ✅ Added safely

@app.route('/notices')
def notice_board():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM notices ORDER BY created_at DESC")
    notices = cur.fetchall()
    conn.close()
    return render_template("notice_board.html", notices=notices)

@app.route('/add-notice', methods=['GET', 'POST'])
def add_notice():
    if request.method == 'POST':
        if not session.get('admin'):
            flash("Unauthorized", "danger")
            return redirect(url_for('notice_board'))

        title = request.form['title']
        content = request.form['content']
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M')

        try:
            with sqlite3.connect(DB_PATH, timeout=5) as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO notices (title, content, created_at) VALUES (?, ?, ?)",
                    (title, content, created_at)
                )
                conn.commit()
            flash("✅ Notice added!", "success")
        except sqlite3.OperationalError as e:
            flash(f"❌ Error adding notice: {e}", "danger")

        return redirect(url_for('notice_board'))

    # fallback GET request
    return redirect(url_for('notice_board'))


@app.route('/delete-notice/<int:notice_id>', methods=['POST'])
def delete_notice(notice_id):
    if not session.get('admin'):
        flash("Unauthorized", "danger")
        return redirect(url_for('notice_board'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    conn.commit()
    conn.close()
    flash("Notice deleted!", "success")
    return redirect(url_for('notice_board'))


@app.route('/set-language', methods=['POST'])
def set_language():
    lang = request.form.get('lang', 'en')
    session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


@app.route('/about')
def about():
    return render_template('about.html', title="About Us")

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        # Yahan aap message ko store kar sakte hain ya print/debug kar sakte hain
        print(f"Contact Form Submission:\nName: {name}\nEmail: {email}\nMessage: {message}")

        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', title="Contact")

@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    gallery_path = os.path.join(app.static_folder, 'images', 'gallery')
    os.makedirs(gallery_path, exist_ok=True)  # Ensure folder exists

    if request.method == 'POST' and 'admin' in session:
        file = request.files.get('gallery_file')
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(gallery_path, filename)
            file.save(save_path)
            flash("✅ Image uploaded to gallery!", "success")
        else:
            flash("⚠️ Please select a valid image file.", "warning")

    images = []
    if os.path.exists(gallery_path):
        images = [f for f in os.listdir(gallery_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]

    return render_template('gallery.html', title="Gallery", images=images)

@app.route('/delete-gallery-image/<filename>', methods=['POST'])
def delete_gallery_image(filename):
    if 'admin' not in session:
        flash("Unauthorized access", "danger")
        return redirect(url_for('gallery'))

    image_path = os.path.join('static', 'images', 'gallery', filename)
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
            flash("🗑 Image deleted successfully!", "success")
        else:
            flash("⚠️ Image not found.", "warning")
    except Exception as e:
        flash(f"❌ Error deleting image: {str(e)}", "danger")

    return redirect(url_for('gallery'))


@app.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Table create karna (agar pehle se nahi hai)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                message TEXT,
                date TEXT
            )
        """)

        from datetime import datetime
        cur.execute("INSERT INTO feedback (name, email, message, date) VALUES (?, ?, ?, ?)",
                    (name, email, message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        conn.commit()
        conn.close()

        flash("✅ Your message has been received!", "success")
        return redirect(url_for('support'))

    return render_template('support.html', title="Help & Support")


@app.route('/admin/feedback')
def view_feedback():
    if 'admin' not in session:
        flash("Admin login required!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM feedback ORDER BY date DESC")
    feedbacks = cur.fetchall()
    conn.close()

    return render_template('feedback_list.html', feedbacks=feedbacks)


@app.route('/student-login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE username = ? AND password = ?", (username, password))
        student = cur.fetchone()
        conn.close()

        if student:
            session['student_id'] = student['id']  # ✅ Correct key
            flash('✅ Student login successful!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('❌ Invalid student credentials!', 'danger')

    return render_template('student_login.html', title="Student Login")


def get_admin(username):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Ensure table exists
    cur.execute("CREATE TABLE IF NOT EXISTS admin (username TEXT, password TEXT)")

    # Try to get the admin with given username
    cur.execute("SELECT * FROM admin WHERE username = ?", (username,))
    admin = cur.fetchone()

    # If no admin exists at all, insert default admin
    if not admin:
        cur.execute("SELECT COUNT(*) FROM admin")
        total_admins = cur.fetchone()[0]
        if total_admins == 0:
            cur.execute("INSERT INTO admin (username, password) VALUES (?, ?)", ('admin', 'admin'))
            conn.commit()
            cur.execute("SELECT * FROM admin WHERE username = ?", (username,))
            admin = cur.fetchone()

    conn.close()
    return admin



@app.route('/student-dashboard', methods=['GET', 'POST'])
def student_dashboard():
    if 'student_id' not in session:
        flash("Please login to access your dashboard.", "warning")
        return redirect(url_for('student_login'))

    student_id = session['student_id']

    if request.method == 'POST':
        table_number = request.form.get('table_number')
        library_timing = request.form.get('library_timing')

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE students SET table_number = ?, library_timing = ? WHERE id = ?",
                    (table_number, library_timing, student_id))
        conn.commit()
        conn.close()

        flash("✅ Successfully updated!", "success")
        return redirect(url_for('student_dashboard'))  # Refresh with new data

    # GET Request
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cur.fetchone()
    conn.close()

    if not student:
        flash("Student not found!", "danger")
        return redirect(url_for('student_login'))

    return render_template('student_dashboard.html', student=student, title="Student Dashboard")




@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = get_admin(username)  # Now passing the username

        if admin and password == admin['password']:
            session['admin'] = username
            flash('Admin login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid admin credentials!', 'danger')

    return render_template('admin_login.html', title="Admin Login")



@app.route('/admin-settings', methods=['GET', 'POST'])
def admin_settings():
    if 'admin' not in session:
        flash('Login as admin to access this page', 'warning')
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        new_username = request.form.get('new_username')
        new_password = request.form.get('new_password')
        new_total_seats = request.form.get('total_seats')
        library_name = request.form.get('library_name')
        library_address = request.form.get('library_address')
        library_phone = request.form.get('library_phone')
        opening_hours = request.form.get('opening_hours')
        about = request.form.get('about')

        # ✅ Update admin credentials
        cur.execute("UPDATE admin SET username = ?, password = ? WHERE username = ?", 
                    (new_username, new_password, session['admin']))
        session['admin'] = new_username  # ✅ update session too

        # ✅ Update library settings
        cur.execute("""
            UPDATE settings SET 
                total_seats = ?,
                library_name = ?,
                library_address = ?,
                library_phone = ?,
                opening_hours = ?,
                about = ?
        """, (new_total_seats, library_name, library_address, library_phone, opening_hours, about))

        conn.commit()
        flash("✅ Admin settings updated!", "success")
        return redirect(url_for('admin_settings'))

    # ✅ Load data to show in form
    current_admin = get_admin(session['admin'])  # <-- FIXED HERE
    cur.execute("SELECT * FROM settings LIMIT 1")
    settings = cur.fetchone()

    conn.close()

    return render_template(
        'admin_settings.html',
        title="Admin Settings",
        admin=current_admin,
        total_seats=settings['total_seats'] if settings else 60,
        settings=settings
    )


@app.context_processor
def inject_library_settings():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM settings LIMIT 1")
    settings = cur.fetchone()
    conn.close()
    return dict(library_settings=settings)


@app.route('/dashboard')
def dashboard():
    if 'admin' in session:
        students = get_students()
        total_students = len(students)
        active_students = sum(1 for s in students if s['status'] == 'active')
        total_seats = get_total_seats()
        empty_seats = total_seats - active_students

        # ✅ Fetch latest 5 notices from DB
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM notices ORDER BY created_at DESC LIMIT 5")
        notices = cur.fetchall()
        conn.close()

        return render_template('dashboard.html',
                               title="Admin Dashboard",
                               total_students=total_students,
                               active_students=active_students,
                               total_seats=total_seats,
                               empty_seats=empty_seats,
                               students=students,
                               notices=notices)
    else:
        flash('Please login as admin!', 'warning')
        return redirect(url_for('admin_login'))


@app.route('/update-seats', methods=['POST'])
def update_seats():
    if 'admin' not in session:
        flash('Login as admin to access this page', 'warning')
        return redirect(url_for('admin_login'))

    new_total_seats = request.form.get('total_seats')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE settings SET total_seats = ?", (new_total_seats,))
    conn.commit()
    conn.close()

    flash("✅ Total seats updated successfully!", "success")
    return redirect(url_for('dashboard'))  # ✅ this matches your route

@app.route('/admission', methods=['GET', 'POST'])
def admission():
    if request.method == 'POST':
        # 🧑‍🎓 Student details
        name = request.form.get('name')
        year = request.form.get('year')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        father_name = request.form.get('father_name')
        exam = request.form.get('exam')
        school_10 = request.form.get('school_10')
        percent_10 = request.form.get('percent_10')
        school_12 = request.form.get('school_12')
        percent_12 = request.form.get('percent_12')
        college_grad = request.form.get('college_grad')
        percent_grad = request.form.get('percent_grad')
        admission = request.form.get('admission')  # ✅ NEW: date field from form
        photo_file = request.files['photo']
        photo_filename = ''

        # 🖼️ Photo Upload
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            unique_name = f"{uuid.uuid4().hex}_{filename}"
            photo_path = os.path.join('static', 'images', unique_name)
            photo_file.save(photo_path)
            photo_filename = unique_name

        # 🔐 Generate Username & Password
        username = generate_username(name)
        password = generate_password()

        # 🗂️ Save into session temporarily
        session['pending_student'] = {
            'name': name, 'year': year, 'gender': gender, 'phone': phone, 'email': email,
            'address': address, 'father_name': father_name, 'exam': exam,
            'school_10': school_10, 'percent_10': percent_10,
            'school_12': school_12, 'percent_12': percent_12,
            'college_grad': college_grad, 'percent_grad': percent_grad,
            'photo': photo_filename,
            'username': username, 'password': password,
            'admission': admission  # ✅ Save date to session
        }

        return redirect(url_for('fees_payment'))

    return render_template('admission.html', title="New Admission")


@app.route('/manage_admissions')
def manage_admissions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE approved = 0")
    students = cur.fetchall()
    conn.close()
    return render_template("manage_admissions.html", students=students)

@app.route('/approve_student/<int:student_id>', methods=['POST'])
def approve_student(student_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE students SET approved = 1 WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash("Student approved successfully!", "success")
    return redirect(url_for('manage_admissions'))

@app.route('/reject_student/<int:student_id>', methods=['POST'])
def reject_student(student_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash("Student rejected and deleted.", "danger")
    return redirect(url_for('manage_admissions'))


@app.route('/fees-payment', methods=['GET', 'POST'])
def fees_payment():
    if 'pending_student' not in session:
        flash("⚠️ Please fill admission form first!", "danger")
        return redirect(url_for('admission'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM fees_settings ORDER BY id DESC LIMIT 1")
    settings = cur.fetchone()

    if request.method == 'POST':
        amount = request.form.get('amount')
        transaction_id = request.form.get('transaction_id')

        if not amount or not transaction_id:
            flash("❌ Amount & Transaction ID are required!", "danger")
            return redirect(url_for('fees_payment'))

        student = session['pending_student']

        # ✅ Now include admission (date) field in DB insert
        cur.execute("""
            INSERT INTO students 
            (name, year, gender, phone, email, address, father_name, exam, 
             school_10, percent_10, school_12, percent_12, college_grad, percent_grad, 
             photo, username, password, admission, fees_amount, transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student['name'], student['year'], student['gender'], student['phone'], student['email'],
            student['address'], student['father_name'], student['exam'],
            student['school_10'], student['percent_10'], student['school_12'], student['percent_12'],
            student['college_grad'], student['percent_grad'],
            student['photo'], student['username'], student['password'],
            student.get('admission'),  # 🗓️ This is the date field from admission form
            amount, transaction_id
        ))
        conn.commit()
        conn.close()
        session.pop('pending_student')

        flash(f"✅ Admission Successful! Username: {student['username']} | Password: {student['password']}", "success")
        return redirect(url_for('admission'))

    return render_template('fees_payment.html', title="Fees Payment", settings=settings)






@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    if 'admin' not in session:
        flash("Admin login required!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # GET: Fetch student data
    cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cur.fetchone()

    if not student:
        conn.close()
        flash("Student not found!", "warning")
        return redirect(url_for('members'))

    if request.method == 'POST':
        name = request.form['name']
        year = request.form['year']
        status = request.form['status']
        admission = request.form.get('admission', 'Yes')

        # Update the student record
        cur.execute("""
            UPDATE students SET name = ?, year = ?, status = ?, admission = ?
            WHERE id = ?
        """, (name, year, status, admission, student_id))
        conn.commit()
        conn.close()

        flash("✅ Student updated successfully!", "success")
        return redirect(url_for('members'))

    conn.close()
    return render_template('edit_student.html', title="Edit Student", student=student)

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if 'admin' not in session:
        flash("Admin login required!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Student deleted successfully.", "success")

    # Check where request came from
    redirect_from = request.form.get('from')
    if redirect_from == 'dashboard':
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('members'))




@app.route('/student-id/<int:student_id>')
def student_id(student_id):
    student = get_student_by_id(student_id)
    if not student:
        flash("Student not found", "danger")
        return redirect(url_for('student_dashboard'))  # yeh sahi route hona chahiye
    return render_template('student_id.html', student=student, title="Library ID")

def get_student_by_id(student_id):
    conn = sqlite3.connect(DB_PATH)  # ✅ use consistent DB_PATH
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cur.fetchone()
    conn.close()
    return student

@app.route('/update-student-info', methods=['POST'])
def update_student_info():
    if 'student_id' not in session:
        flash("Login required", "warning")
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    table_number = request.form.get('table_number')
    library_timing = request.form.get('library_timing')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE students SET table_number = ?, library_timing = ? WHERE id = ?", 
                (table_number, library_timing, student_id))
    conn.commit()
    conn.close()

    flash("✅ Info updated successfully!", "success")
    return redirect(url_for('student_dashboard'))


@app.route('/reset_password', methods=['POST'])
def reset_password():
    if 'student_id' not in session:
        return redirect(url_for('student_login'))

    student_id = session['student_id']
    new_password = request.form.get('new_password')

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE students SET password = ? WHERE id = ?", (new_password, student_id))
    conn.commit()
    conn.close()

    flash("Password updated successfully!", "success")
    return redirect(url_for('student_dashboard'))


@app.route('/members')
def members():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    is_admin = 'admin' in session

    if is_admin:
        cur.execute("SELECT * FROM students ORDER BY year DESC")
    else:
        cur.execute("""
            SELECT id, name, gender, photo, exam, address, college_grad, percent_grad,
                   father_name, table_number, library_timing, status 
            FROM students 
            WHERE status = 'active' 
            ORDER BY year DESC
        """)

    students = cur.fetchall()
    conn.close()

    return render_template('members.html', title="Current Student Members", students=students, is_admin=is_admin)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d-%m-%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except (ValueError, TypeError):
        return 'Not Set'




@app.route('/fees', methods=['GET', 'POST'])
def fees():
    if 'admin' not in session:
        flash("Login as admin to access this page", "warning")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        phonepe_number = request.form.get('phonepe_number')
        qr_file = request.files.get('qr_image')
        qr_filename = ''

        if qr_file and qr_file.filename != '':
            filename = secure_filename(qr_file.filename)
            qr_filename = f"{uuid.uuid4().hex}_{filename}"
            qr_file.save(os.path.join('static', 'qr', qr_filename))

        cur.execute("SELECT * FROM fees_settings ORDER BY id DESC LIMIT 1")
        existing = cur.fetchone()
        if existing:
            if qr_filename != '':
                cur.execute("UPDATE fees_settings SET phonepe_number=?, qr_image=? WHERE id=?", 
                            (phonepe_number, qr_filename, existing['id']))
            else:
                cur.execute("UPDATE fees_settings SET phonepe_number=? WHERE id=?", 
                            (phonepe_number, existing['id']))
        else:
            cur.execute("INSERT INTO fees_settings (phonepe_number, qr_image) VALUES (?, ?)", 
                        (phonepe_number, qr_filename))

        conn.commit()
        flash("✅ Payment info updated!", "success")
        return redirect(url_for('fees'))

    cur.execute("SELECT * FROM fees_settings ORDER BY id DESC LIMIT 1")
    payment_info = cur.fetchone()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()

    return render_template('fees.html', title="Fees Panel", payment_info=payment_info, students=students)



@app.route('/update-fee/<int:student_id>', methods=['POST'])
def update_fee(student_id):
    status = request.form.get('fee_status')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("UPDATE students SET fees_status = ? WHERE id = ?", (status, student_id))
        conn.commit()
    except Exception as e:
        print(f"Error updating fee status: {e}")
    conn.close()
    flash("💸 Fee status updated!", "success")
    return redirect(url_for('fees'))

@app.route('/delete-fees-student/<int:student_id>', methods=['POST'])
def delete_fees_student(student_id):
    if 'admin' not in session:
        flash("⚠️ Admin login required!", "danger")
        return redirect(url_for('admin_login'))

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        conn.close()
        flash("🗑️ Student deleted from fees panel!", "success")
    except Exception as e:
        flash(f"❌ Error deleting student: {e}", "danger")

    return redirect(url_for('fees'))


@app.route('/update_fee_month/<int:student_id>', methods=['POST'])
def update_fee_month(student_id):
    month = request.form.get('month')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE students SET month = ? WHERE id = ?", (month, student_id))
    conn.commit()
    conn.close()
    flash('Month updated successfully.', 'success')
    return redirect(url_for('fees'))



@app.route('/expenses')
def expenses():
    if 'admin' in session:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses ORDER BY date DESC")
        expenses = cur.fetchall()
        conn.close()
        return render_template('bill_panel.html', title="Library Expenses", expenses=expenses)
    flash("Please login as admin!", "danger")
    return redirect(url_for('admin_login'))

@app.route('/add-expense', methods=['POST'])
def add_expense():
    if 'admin' in session:
        amount = request.form.get('amount')
        category = request.form.get('category')
        source = request.form.get('source')
        description = request.form.get('description')
        date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO expenses (amount, category, source, description, date) VALUES (?, ?, ?, ?, ?)",
                    (amount, category, source, description, date))
        conn.commit()
        conn.close()
        flash("Expense added successfully!", "success")
        return redirect(url_for('expenses'))
    flash("Unauthorized access!", "danger")
    return redirect(url_for('admin_login'))

@app.route('/delete-expense/<int:expense_id>')
def delete_expense(expense_id):
    if 'admin' in session:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()
        flash("🗑️ Expense deleted!", "info")
        return redirect(url_for('expenses'))
    flash("Unauthorized access!", "danger")
    return redirect(url_for('admin_login'))

@app.route('/export-expenses')
def export_expenses():
    if 'admin' in session:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses ORDER BY date DESC")
        expenses = cur.fetchall()
        conn.close()
        def generate():
            yield 'ID,Amount,Category,Source,Description,Date\n'
            for row in expenses:
                yield f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]}\n"
        return Response(generate(), mimetype='text/csv',
                        headers={"Content-Disposition": "attachment;filename=library_expenses.csv"})
    flash("Unauthorized access!", "danger")
    return redirect(url_for('admin_login'))

@app.route('/donations', methods=['GET', 'POST'])
def donations():
    is_admin = 'admin' in session
    db = get_db()
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    # Handle form submissions
    if request.method == 'POST':
        if 'phonepe_id' in request.form and is_admin:
            phonepe_id = request.form.get('phonepe_id')
            qr_file = request.files.get('qr_code')
            qr_filename = None

            if qr_file and qr_file.filename:
                qr_filename = secure_filename(qr_file.filename)
                qr_path = os.path.join('static', 'images', qr_filename)
                qr_file.save(qr_path)

            cur.execute("SELECT id FROM payment_settings LIMIT 1")
            existing = cur.fetchone()

            if existing:
                cur.execute("UPDATE payment_settings SET phonepe_id = ?, qr_code_path = ? WHERE id = ?",
                            (phonepe_id, qr_filename, existing['id']))
            else:
                cur.execute("INSERT INTO payment_settings (phonepe_id, qr_code_path) VALUES (?, ?)",
                            (phonepe_id, qr_filename))
            db.commit()
            flash("✅ Payment settings updated!", "success")

        elif not is_admin:
            # Public donation
            name = request.form['name']
            date = request.form['date']
            item = request.form['item']
            description = request.form['description']
            photo = request.files.get('photo')

            photo_filename = None
            if photo and photo.filename:
                photo_filename = secure_filename(photo.filename)
                photo.save(os.path.join('static', 'images', photo_filename))

            cur.execute("INSERT INTO donations (name, date, item, description, photo) VALUES (?, ?, ?, ?, ?)",
                        (name, date, item, description, photo_filename))
            db.commit()
            flash("✅ Donation submitted successfully!", "success")

    # Fetch data for rendering
    donations = cur.execute("SELECT * FROM donations ORDER BY date DESC").fetchall()
    cur.execute("SELECT phonepe_id, qr_code_path FROM payment_settings LIMIT 1")
    row = cur.fetchone()
    phonepe_id = row['phonepe_id'] if row else None
    qr_code_path = row['qr_code_path'] if row else None

    return render_template('donations.html',
                           donations=donations,
                           phonepe_id=phonepe_id,
                           qr_code_path=qr_code_path,
                           is_admin=is_admin)



@app.route('/donation/edit/<int:donation_id>', methods=['GET', 'POST'])
def edit_donation(donation_id):
    if 'admin' not in session:
        flash("Admin access required!", "danger")
        return redirect(url_for('donations'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM donations WHERE id = ?", (donation_id,))
    donation = cur.fetchone()

    if not donation:
        flash("Donation not found.", "warning")
        return redirect(url_for('donations'))

    if request.method == 'POST':
        name = request.form.get('name')
        date = request.form.get('date')
        item = request.form.get('item')
        description = request.form.get('description')

        # Handle photo update
        photo_file = request.files.get('photo')
        photo_filename = donation[5]  # existing photo
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            photo_filename = f"{uuid.uuid4().hex}_{filename}"
            photo_file.save(os.path.join('static', 'images', photo_filename))

        cur.execute("""
            UPDATE donations SET name=?, date=?, item=?, description=?, photo=? WHERE id=?
        """, (name, date, item, description, photo_filename, donation_id))
        conn.commit()
        conn.close()
        flash("Donation updated successfully!", "success")
        return redirect(url_for('donations'))

    conn.close()
    return render_template('edit_donation.html', donation=donation)

@app.route('/donation/delete/<int:donation_id>', methods=['POST'])
def delete_donation(donation_id):
    if 'admin' not in session:
        flash("Admin access required!", "danger")
        return redirect(url_for('donations'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM donations WHERE id = ?", (donation_id,))
    conn.commit()
    conn.close()

    flash("Donation deleted successfully.", "success")
    return redirect(url_for('donations'))

@app.route('/donation/print/<int:donation_id>')
def print_donation(donation_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM donations WHERE id = ?", (donation_id,))
    donation = cur.fetchone()
    conn.close()

    if not donation:
        flash("Donation not found.", "warning")
        return redirect(url_for('donations'))

    return render_template('print_donation.html', donation=donation)

@app.route('/admin/payment-settings', methods=['GET', 'POST'])
def update_payment_settings():
    if 'admin' not in session:
        flash("Admin access required!", "danger")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # enable dict-like access
    cur = conn.cursor()

    if request.method == 'POST':
        phonepe_id = request.form.get('phonepe_id')
        qr_file = request.files.get('qr_code')

        qr_filename = ''
        if qr_file and qr_file.filename != '':
            filename = secure_filename(qr_file.filename)
            qr_filename = f"{uuid.uuid4().hex}_{filename}"
            qr_file.save(os.path.join('static', 'images', qr_filename))

            cur.execute("""
                UPDATE payment_settings 
                SET phonepe_id = ?, qr_code_path = ?
                WHERE id = 1
            """, (phonepe_id, qr_filename))
        else:
            cur.execute("""
                UPDATE payment_settings 
                SET phonepe_id = ?
                WHERE id = 1
            """, (phonepe_id,))

        conn.commit()
        flash("✅ Payment settings updated!", "success")

    cur.execute("SELECT * FROM payment_settings WHERE id = 1")
    settings = cur.fetchone()
    conn.close()
    return render_template("admin_payment_settings.html", settings=settings)



@app.route('/authorities', methods=['GET', 'POST'])
def authorities():
    if 'admin' not in session:
        flash("Login as admin to manage authorities.", "warning")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        phone = request.form.get('phone')
        email = request.form.get('email')

        photo_file = request.files.get('photo')
        photo_filename = ''
        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            photo_filename = f"{uuid.uuid4().hex}_{filename}"
            photo_file.save(os.path.join('static', 'images', photo_filename))

        cur.execute("INSERT INTO authorities (name, role, phone, email, photo) VALUES (?, ?, ?, ?, ?)",
                    (name, role, phone, email, photo_filename))
        conn.commit()
        flash("✅ Authority added successfully!", "success")
        return redirect(url_for('authorities'))

    cur.execute("SELECT * FROM authorities")
    authority_list = cur.fetchall()
    conn.close()

    return render_template('authorities.html', title="Library Authorities", authorities=authority_list, is_admin=True)


# Public display page
@app.route('/library-authority')
def library_authority():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM authorities")
    members = cur.fetchall()
    conn.close()
    return render_template('library_authority.html', title="Library Authority Info", members=members)

@app.route('/authority/edit/<int:auth_id>', methods=['GET', 'POST'])
def edit_authority(auth_id):
    if 'admin' not in session:
        flash("Login as admin to edit authority.", "warning")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        phone = request.form.get('phone')
        email = request.form.get('email')
        photo_file = request.files.get('photo')

        if photo_file and photo_file.filename != '':
            filename = secure_filename(photo_file.filename)
            photo_filename = f"{uuid.uuid4().hex}_{filename}"
            photo_file.save(os.path.join('static', 'images', photo_filename))
            cur.execute("UPDATE authorities SET name=?, role=?, phone=?, email=?, photo=? WHERE id=?",
                        (name, role, phone, email, photo_filename, auth_id))
        else:
            cur.execute("UPDATE authorities SET name=?, role=?, phone=?, email=? WHERE id=?",
                        (name, role, phone, email, auth_id))

        conn.commit()
        conn.close()
        flash("✅ Authority updated successfully!", "success")
        return redirect(url_for('authorities'))

    cur.execute("SELECT * FROM authorities WHERE id=?", (auth_id,))
    authority = cur.fetchone()
    conn.close()

    return render_template('edit_authority.html', authority=authority)


@app.route('/authority/delete/<int:auth_id>', methods=['POST'])
def delete_authority(auth_id):
    if 'admin' not in session:
        flash("Login as admin to delete authority.", "warning")
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM authorities WHERE id=?", (auth_id,))
    conn.commit()
    conn.close()

    flash("🗑️ Authority deleted successfully!", "info")
    return redirect(url_for('authorities'))



@app.route('/monthly-report')
def monthly_report():
    if 'admin' in session:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT strftime('%Y-%m', date) AS month, 
                   SUM(amount) as total
            FROM expenses
            GROUP BY month
            ORDER BY month DESC
        """)
        report = cur.fetchall()
        conn.close()
        return render_template('monthly_report.html', title="Monthly Expense Report", report=report)
    flash("Unauthorized access!", "danger")
    return redirect(url_for('admin_login'))

@app.route('/toggle-status/<int:student_id>', methods=['POST'])
def toggle_status(student_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT status FROM students WHERE id = ?", (student_id,))
    row = cur.fetchone()
    if row:
        new_status = 'inactive' if row[0] == 'active' else 'active'
        cur.execute("UPDATE students SET status = ? WHERE id = ?", (new_status, student_id))
        conn.commit()
    conn.close()
    flash("Student status updated", "success")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    update_settings_table_schema() 
    app.run(debug=True)