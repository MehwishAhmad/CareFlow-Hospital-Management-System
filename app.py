from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, date
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'change-this-secret-key'
DB_PATH = Path(__file__).with_name('hospital.db')

ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASSWORD = 'admin123'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialization TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        fee REAL DEFAULT 0,
        status TEXT DEFAULT 'Active'
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        phone TEXT,
        disease TEXT,
        doctor_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        fee REAL DEFAULT 0,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    )''')
    conn.commit()

    doctor_count = cur.execute('SELECT COUNT(*) FROM doctors').fetchone()[0]
    if doctor_count == 0:
        cur.executemany('INSERT INTO doctors (name, specialization, phone, email, fee, status) VALUES (?, ?, ?, ?, ?, ?)', [
            ('Dr. Ayesha Khan', 'Cardiologist', '03001234567', 'ayesha@hospital.com', 2500, 'Active'),
            ('Dr. Ali Raza', 'Dermatologist', '03007654321', 'ali@hospital.com', 1800, 'Active'),
            ('Dr. Sara Ahmed', 'Pediatrician', '03009871234', 'sara@hospital.com', 1500, 'Active'),
        ])
        conn.commit()

    patient_count = cur.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
    if patient_count == 0:
        cur.executemany('INSERT INTO patients (name, age, gender, phone, disease, doctor_id) VALUES (?, ?, ?, ?, ?, ?)', [
            ('Ahmed Malik', 32, 'Male', '03110000001', 'Chest Pain', 1),
            ('Fatima Noor', 24, 'Female', '03110000002', 'Skin Allergy', 2),
            ('Hassan Ali', 8, 'Male', '03110000003', 'Fever', 3),
        ])
        conn.commit()
        cur.executemany('INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, fee) VALUES (?, ?, ?, ?, ?, ?)', [
            (1, 1, str(date.today()), '10:00', 'Completed', 2500),
            (2, 2, str(date.today()), '12:30', 'Pending', 1800),
            (3, 3, str(date.today()), '15:00', 'Pending', 1500),
        ])
        conn.commit()
    conn.close()


def login_required(fn):
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_name'] = 'Admin'
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    today = str(date.today())
    stats = {
        'patients': conn.execute('SELECT COUNT(*) FROM patients').fetchone()[0],
        'doctors': conn.execute('SELECT COUNT(*) FROM doctors').fetchone()[0],
        'appointments': conn.execute('SELECT COUNT(*) FROM appointments').fetchone()[0],
        'today': conn.execute('SELECT COUNT(*) FROM appointments WHERE appointment_date=?', (today,)).fetchone()[0],
        'revenue': conn.execute("SELECT COALESCE(SUM(fee),0) FROM appointments WHERE status='Completed'").fetchone()[0]
    }
    recent = conn.execute('''SELECT a.*, p.name AS patient_name, d.name AS doctor_name
                             FROM appointments a
                             JOIN patients p ON p.id=a.patient_id
                             JOIN doctors d ON d.id=a.doctor_id
                             ORDER BY a.id DESC LIMIT 6''').fetchall()
    conn.close()
    return render_template('dashboard.html', stats=stats, recent=recent)


@app.route('/doctors', methods=['GET', 'POST'])
@login_required
def doctors():
    conn = get_db()
    if request.method == 'POST':
        conn.execute('INSERT INTO doctors (name, specialization, phone, email, fee, status) VALUES (?, ?, ?, ?, ?, ?)',
                     (request.form['name'], request.form['specialization'], request.form['phone'], request.form['email'], request.form['fee'], request.form['status']))
        conn.commit()
        flash('Doctor added successfully', 'success')
        return redirect(url_for('doctors'))
    rows = conn.execute('SELECT * FROM doctors ORDER BY id DESC').fetchall()
    search = request.args.get('search', '')

    if search:
        rows = conn.execute(
            'SELECT * FROM doctors WHERE name LIKE ? OR specialization LIKE ? OR phone LIKE ?',
            (f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM doctors').fetchall()
    conn.close()
    return render_template('doctors.html', doctors=rows)


@app.route('/patients', methods=['GET', 'POST'])
def patients():
    conn = get_db()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        phone = request.form['phone']
        disease = request.form['disease']

        conn.execute(
            'INSERT INTO patients (name, age, gender, phone, disease) VALUES (?, ?, ?, ?, ?)',
            (name, age, gender, phone, disease)
        )
        conn.commit()

    search = request.args.get('search', '')

    if search:
        rows = conn.execute(
            'SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ? OR disease LIKE ?',
            (f'%{search}%', f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM patients').fetchall()

    conn.close()
    return render_template('patients.html', patients=rows, search=search)

@app.route('/appointments', methods=['GET', 'POST'])
@login_required
def appointments():
    conn = get_db()
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        fee_row = conn.execute('SELECT fee FROM doctors WHERE id=?', (doctor_id,)).fetchone()
        fee = fee_row['fee'] if fee_row else 0
        conn.execute('''INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, fee)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (request.form['patient_id'], doctor_id, request.form['appointment_date'], request.form['appointment_time'], request.form['status'], fee))
        conn.commit()
        flash('Appointment added successfully', 'success')
        return redirect(url_for('appointments'))
    patients = conn.execute('SELECT * FROM patients ORDER BY name').fetchall()
    doctors = conn.execute('SELECT * FROM doctors WHERE status="Active" ORDER BY name').fetchall()
    rows = conn.execute('''SELECT a.*, p.name AS patient_name, d.name AS doctor_name
                           FROM appointments a
                           JOIN patients p ON p.id=a.patient_id
                           JOIN doctors d ON d.id=a.doctor_id
                           ORDER BY a.id DESC''').fetchall()
    conn.close()
    return render_template('appointments.html', appointments=rows, patients=patients, doctors=doctors)


@app.route('/reports')
@login_required
def reports():
    conn = get_db()
    rows = conn.execute('''SELECT a.appointment_date, COUNT(*) AS total_appointments, COALESCE(SUM(a.fee),0) AS revenue
                           FROM appointments a
                           GROUP BY a.appointment_date
                           ORDER BY a.appointment_date DESC''').fetchall()
    conn.close()
    return render_template('reports.html', reports=rows)


@app.route('/delete/<table>/<int:item_id>')
@login_required
def delete_item(table, item_id):
    if table not in ['doctors', 'patients', 'appointments']:
        flash('Invalid delete request', 'error')
        return redirect(url_for('dashboard'))
    conn = get_db()
    conn.execute(f'DELETE FROM {table} WHERE id=?', (item_id,))
    conn.commit()
    conn.close()
    flash('Record deleted successfully', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/update_appointment_status/<int:id>', methods=['POST'])
def update_appointment_status(id):
    status = request.form['status']

    conn = get_db()
    conn.execute(
        'UPDATE appointments SET status = ? WHERE id = ?',
        (status, id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('appointments'))


@app.route('/edit_patient/<int:id>', methods=['GET', 'POST'])
def edit_patient(id):
    conn = get_db()
    patient = conn.execute('SELECT * FROM patients WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        phone = request.form['phone']
        disease = request.form['disease']

        conn.execute('''
            UPDATE patients
            SET name = ?, age = ?, gender = ?, phone = ?, disease = ?
            WHERE id = ?
        ''', (name, age, gender, phone, disease, id))

        conn.commit()
        conn.close()
        return redirect(url_for('patients'))

    conn.close()
    return render_template('edit_patient.html', patient=patient)


@app.route('/edit_doctor/<int:id>', methods=['GET', 'POST'])
def edit_doctor(id):
    conn = get_db()
    doctor = conn.execute('SELECT * FROM doctors WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        phone = request.form['phone']
        email = request.form['email']
        fee = request.form['fee']
        status = request.form['status']

        conn.execute('''
            UPDATE doctors
            SET name = ?, specialization = ?, phone = ?, email = ?, fee = ?, status = ?
            WHERE id = ?
        ''', (name, specialization, phone, email, fee, status, id))

        conn.commit()
        conn.close()
        return redirect(url_for('doctors'))

    conn.close()
    return render_template('edit_doctor.html', doctor=doctor)



if __name__ == '__main__':
    init_db()
    app.run(debug=True)
