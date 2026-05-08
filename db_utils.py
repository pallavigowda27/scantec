import sqlite3
import datetime
import hashlib
import os
import smtplib
from email.mime.text import MIMEText

DB_FILE = os.path.join(os.path.dirname(__file__), "scantec_history.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            email TEXT,
            two_fa_secret TEXT,
            two_fa_enabled BOOLEAN DEFAULT 0
        )
    ''')
    # Scans table
    c.execute('''
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            prediction TEXT,
            confidence REAL,
            feedback TEXT,
            doctor_notes TEXT,
            patient_name TEXT,
            patient_age TEXT,
            user_id INTEGER,
            report_path TEXT,
            priority_level TEXT,
            vlm_analysis TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Comments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            user_id INTEGER,
            comment TEXT,
            timestamp TEXT,
            FOREIGN KEY (scan_id) REFERENCES scans (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Audit logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            timestamp TEXT,
            details TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    # Check for new columns and add if missing
    c.execute("PRAGMA table_info(scans)")
    columns = [info[1] for info in c.fetchall()]
    if 'patient_name' not in columns:
        c.execute("ALTER TABLE scans ADD COLUMN patient_name TEXT")
    if 'patient_age' not in columns:
        c.execute("ALTER TABLE scans ADD COLUMN patient_age TEXT")
    if 'user_id' not in columns:
        c.execute("ALTER TABLE scans ADD COLUMN user_id INTEGER")
    if 'report_path' not in columns:
        try:
            c.execute("ALTER TABLE scans ADD COLUMN report_path TEXT")
        except sqlite3.OperationalError:
            pass
    if 'priority_level' not in columns:
        try:
            c.execute("ALTER TABLE scans ADD COLUMN priority_level TEXT")
        except sqlite3.OperationalError:
            pass
    if 'vlm_analysis' not in columns:
        try:
            c.execute("ALTER TABLE scans ADD COLUMN vlm_analysis TEXT")
        except sqlite3.OperationalError:
            pass
    if 'archived' not in columns:
        try:
            c.execute("ALTER TABLE scans ADD COLUMN archived BOOLEAN DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    
    # Check users table
    c.execute("PRAGMA table_info(users)")
    user_columns = [info[1] for info in c.fetchall()]
    if 'email' not in user_columns:
        c.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if 'two_fa_secret' not in user_columns:
        c.execute("ALTER TABLE users ADD COLUMN two_fa_secret TEXT")
    if 'two_fa_enabled' not in user_columns:
        c.execute("ALTER TABLE users ADD COLUMN two_fa_enabled BOOLEAN DEFAULT 0")
    
    # Create default users if not exist
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        # Create default admin and user
        c.execute('INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)', ('doctor', hash_password('pass'), 'admin', 'doctor@example.com'))
        c.execute('INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)', ('patient', hash_password('pass'), 'user', 'patient@example.com'))
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, role, email=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed = hash_password(password)
    try:
        c.execute('INSERT INTO users (username, password, role, email) VALUES (?, ?, ?, ?)', (username, hashed, role, email))
        conn.commit()
        user_id = c.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    conn.close()
    return user_id

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute('SELECT id, role FROM users WHERE username = ? AND password = ?', (username, hashed))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0], result[1]  # user_id, role
    return None, None

def get_username(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Unknown User"

def insert_scan(prediction, confidence, patient_name="", patient_age="", user_id=None, priority_level="Routine", vlm_analysis=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO scans (timestamp, prediction, confidence, feedback, doctor_notes, patient_name, patient_age, user_id, priority_level, vlm_analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, prediction, confidence, None, None, patient_name, patient_age, user_id, priority_level, vlm_analysis))
    scan_id = c.lastrowid
    conn.commit()
    conn.close()
    return scan_id

def update_feedback(scan_id, feedback):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE scans SET feedback = ? WHERE id = ?', (feedback, scan_id))
    conn.commit()
    conn.close()

def update_notes(scan_id, notes):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE scans SET doctor_notes = ? WHERE id = ?', (notes, scan_id))
    conn.commit()
    conn.close()

def update_report_path(scan_id, report_path):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE scans SET report_path = ? WHERE id = ?', (report_path, scan_id))
    conn.commit()
    conn.close()

def get_recent_scans(limit=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, prediction, confidence, feedback, patient_name, patient_age, user_id FROM scans ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    
    # Format to list of dicts
    history = []
    for r in rows:
        history.append({
            "id": r[0],
            "timestamp": r[1],
            "prediction": r[2],
            "confidence": r[3],
            "feedback": r[4],
            "patient_name": r[5],
            "patient_age": r[6],
            "user_id": r[7]
        })
    return history

def get_scans_for_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, prediction, confidence, feedback, doctor_notes, report_path, priority_level, vlm_analysis FROM scans WHERE user_id = ? ORDER BY id DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    scans = []
    for r in rows:
        scans.append({
            "id": r[0],
            "timestamp": r[1],
            "prediction": r[2],
            "confidence": r[3],
            "feedback": r[4],
            "doctor_notes": r[5],
            "report_path": r[6],
            "priority_level": r[7],
            "vlm_analysis": r[8]
        })
    return scans

def get_all_scans():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, prediction, confidence, feedback, doctor_notes, patient_name, patient_age, user_id, report_path, priority_level, vlm_analysis FROM scans ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    scans = []
    for r in rows:
        scans.append({
            "id": r[0],
            "timestamp": r[1],
            "prediction": r[2],
            "confidence": r[3],
            "feedback": r[4],
            "doctor_notes": r[5],
            "patient_name": r[6],
            "patient_age": r[7],
            "user_id": r[8],
            "report_path": r[9],
            "priority_level": r[10],
            "vlm_analysis": r[11]
        })
    return scans

def update_password(user_id, new_password):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    hashed = hash_password(new_password)
    c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, user_id))
    conn.commit()
    conn.close()

def get_username(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT username FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else "Unknown User"

def get_user_email(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT email FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else ""

def update_user_email(user_id, email):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET email = ? WHERE id = ?', (email, user_id))
    conn.commit()
    conn.close()

def insert_comment(scan_id, user_id, comment):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO comments (scan_id, user_id, comment, timestamp) VALUES (?, ?, ?, ?)', (scan_id, user_id, comment, timestamp))
    conn.commit()
    conn.close()

def get_comments_for_scan(scan_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT c.comment, c.timestamp, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE c.scan_id = ? ORDER BY c.timestamp', (scan_id,))
    rows = c.fetchall()
    conn.close()
    comments = []
    for r in rows:
        comments.append({"comment": r[0], "timestamp": r[1], "username": r[2]})
    return comments

def log_audit(user_id, action, details=""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO audit_logs (user_id, action, timestamp, details) VALUES (?, ?, ?, ?)', (user_id, action, timestamp, details))
    conn.commit()
    conn.close()

def get_audit_logs(limit=50):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT a.action, a.timestamp, a.details, u.username FROM audit_logs a JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    logs = []
    for r in rows:
        logs.append({"action": r[0], "timestamp": r[1], "details": r[2], "username": r[3]})
    return logs

def get_user_2fa_secret(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT two_fa_secret, two_fa_enabled FROM users WHERE id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result if result else (None, False)

def update_user_2fa(user_id, secret, enabled):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET two_fa_secret = ?, two_fa_enabled = ? WHERE id = ?', (secret, enabled, user_id))
    conn.commit()
    conn.close()

def export_scans_to_csv():
    import csv
    scans = get_all_scans()
    csv_path = "scans_export.csv"
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['id', 'timestamp', 'prediction', 'confidence', 'patient_name', 'patient_age', 'user_id', 'report_path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for scan in scans:
            writer.writerow(scan)
    return csv_path

def import_scans_from_csv(csv_path):
    import csv
    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Insert scan, but since id is auto, and user_id might not match, perhaps skip id
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''
                INSERT INTO scans (timestamp, prediction, confidence, patient_name, patient_age, user_id, report_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['timestamp'], row['prediction'], float(row['confidence']), row['patient_name'], row['patient_age'], int(row['user_id']), row.get('report_path')))
            conn.commit()
            conn.close()

def send_email(to_email, subject, body):
    # Mock email sending
    print(f"Sending email to {to_email}: {subject} - {body}")
    # In real app, use smtplib
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = 'noreply@scantec.com'
    # msg['To'] = to_email
    # server = smtplib.SMTP('smtp.example.com')
    # server.login("username", "password")
    # server.sendmail("noreply@scantec.com", to_email, msg.as_string())
    # server.quit()

def export_scans_to_csv():
    import csv
    scans = get_all_scans()
    with open('scans_export.csv', 'w', newline='') as csvfile:
        fieldnames = ['id', 'timestamp', 'prediction', 'confidence', 'patient_name', 'patient_age', 'doctor_notes', 'report_path']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for scan in scans:
            writer.writerow({k: v for k, v in scan.items() if k in fieldnames})
    return 'scans_export.csv'

def send_email(to_email, subject, body):
    # Simple SMTP setup - replace with your email credentials
    sender_email = "your_email@gmail.com"
    sender_password = "your_password"
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = to_email

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False

def archive_scan(scan_id):
    """Archive a scan (soft delete)"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE scans SET archived = 1 WHERE id = ?', (scan_id,))
    conn.commit()
    conn.close()

def unarchive_scan(scan_id):
    """Unarchive a scan"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE scans SET archived = 0 WHERE id = ?', (scan_id,))
    conn.commit()
    conn.close()

def delete_scan(scan_id):
    """Permanently delete a scan"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Delete comments first (foreign key)
    c.execute('DELETE FROM comments WHERE scan_id = ?', (scan_id,))
    # Delete the scan
    c.execute('DELETE FROM scans WHERE id = ?', (scan_id,))
    conn.commit()
    conn.close()

def get_archived_scans(user_id=None):
    """Get all archived scans"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if user_id:
        c.execute('SELECT * FROM scans WHERE archived = 1 AND user_id = ? ORDER BY timestamp DESC', (user_id,))
    else:
        c.execute('SELECT * FROM scans WHERE archived = 1 ORDER BY timestamp DESC')
    scans = [dict(zip([description[0] for description in c.description], row)) for row in c.fetchall()]
    conn.close()
    return scans

def get_all_scans_with_filter(include_archived=False):
    """Get all scans with optional archive filter"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if include_archived:
        c.execute('SELECT * FROM scans ORDER BY timestamp DESC')
    else:
        c.execute('SELECT * FROM scans WHERE archived = 0 ORDER BY timestamp DESC')
    scans = [dict(zip([description[0] for description in c.description], row)) for row in c.fetchall()]
    conn.close()
    return scans
