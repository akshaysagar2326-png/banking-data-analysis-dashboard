from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'banking_secret_key_2026'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            username TEXT UNIQUE,
            email TEXT,
            phone TEXT,
            dob TEXT,
            password TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ================= VALIDATIONS =================

def validate_password(password):
    pattern = r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
    return re.match(pattern, password)


def normalize_columns(df):
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
    return df


def detect_column(columns, keywords):
    for col in columns:
        for keyword in keywords:
            if keyword in col:
                return col
    return None


# ================= AUTH ROUTES =================

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        dob = request.form['dob']
        password = request.form['password']

        if not validate_password(password):
            return jsonify({'status': 'error', 'message': 'Weak password'})

        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users(full_name, username, email, phone, dob, password)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (full_name, username, email, phone, dob, hashed_password))
            conn.commit()
            conn.close()

            return jsonify({'status': 'success'})

        except sqlite3.IntegrityError:
            return jsonify({'status': 'error', 'message': 'Username already exists'})

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[6], password):
            session['user'] = username
            return jsonify({'status': 'success'})

        return jsonify({'status': 'error', 'message': 'Invalid username or password'})

    return render_template('login.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        dob = request.form['dob']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM users WHERE username=? AND dob=?', (username, dob))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['reset_user'] = username
            return jsonify({'status': 'success'})

        return jsonify({'status': 'error', 'message': 'Invalid username or DOB'})

    return render_template('forgot_password.html')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user' not in session:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']

        if not validate_password(password):
            return jsonify({'status': 'error', 'message': 'Weak password'})

        hashed_password = generate_password_hash(password)

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE users SET password=? WHERE username=?
        ''', (hashed_password, session['reset_user']))

        conn.commit()
        conn.close()

        session.pop('reset_user', None)

        return jsonify({'status': 'success'})

    return render_template('reset_password.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    return render_template('dashboard.html', user=session['user'])


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    session['dataset'] = filepath

    return jsonify({'status': 'success'})


@app.route('/analysis', methods=['POST'])
def analysis():
    if 'dataset' not in session:
        return jsonify({'status': 'error', 'message': 'Upload dataset first'})

    try:
        df = pd.read_csv(session['dataset'])
        df = normalize_columns(df)

        loan_col = detect_column(df.columns, ['loan'])
        deposit_col = detect_column(df.columns, ['deposit'])
        balance_col = detect_column(df.columns, ['balance'])
        date_col = detect_column(df.columns, ['date'])

        if not balance_col:
            return jsonify({'status': 'error', 'message': 'Balance column not found'})

        start_date = request.json.get('start_date')
        end_date = request.json.get('end_date')

        if date_col and start_date and end_date:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)

            df = df[(df[date_col] >= start) & (df[date_col] <= end)]

        if df.empty:
            return jsonify({'status': 'error', 'message': 'No data after filtering'})

        total_loans = float(df[loan_col].sum()) if loan_col else 0
        total_deposits = float(df[deposit_col].sum()) if deposit_col else 0
        average_balance = float(df[balance_col].mean())

        low = len(df[df[balance_col] < 50000])
        medium = len(df[(df[balance_col] >= 50000) & (df[balance_col] <= 150000)])
        high = len(df[df[balance_col] > 150000])

        return jsonify({
            'status': 'success',
            'total_loans': round(total_loans, 2),
            'total_deposits': round(total_deposits, 2),
            'average_balance': round(average_balance, 2),
            'segmentation': {
                'low': low,
                'medium': medium,
                'high': high
            }
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
   if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )