# database.py - With auth_method support (face/fingerprint/both)
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


def get_writable_dir():
    """Returns directory next to .exe (frozen) or script directory (dev)."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class Database:
    _instance = None  # shared connection

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(get_writable_dir(), "smart_attendance.db")
        self.db_path = db_path
        # Reuse existing connection if already open
        if Database._instance is None:
            conn = sqlite3.connect(db_path, check_same_thread=False,
                                   timeout=10)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            Database._instance = conn
        self.conn   = Database._instance
        self.cursor = self.conn.cursor()
        self.create_tables()
        self._migrate()
        self.clean_old_records()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_name TEXT UNIQUE NOT NULL,
                phone_number TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                father_name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL,
                reg_number TEXT UNIQUE NOT NULL,
                semester INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                auth_method TEXT DEFAULT 'face',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                roll_number TEXT NOT NULL,
                semester INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                semester INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                subject_name TEXT NOT NULL,
                teacher_name TEXT NOT NULL,
                time_start TEXT NOT NULL,
                time_end TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(semester, slot)
            )
        ''')
        self.conn.commit()

    def _migrate(self):
        """Add auth_method column if upgrading from old database."""
        try:
            self.cursor.execute(
                "ALTER TABLE students ADD COLUMN auth_method TEXT DEFAULT 'face'")
            self.conn.commit()
            print("[db] Migrated: added auth_method column")
        except sqlite3.OperationalError:
            pass  # column already exists

    def change_admin_password(self, admin_name, old_password, new_password):
        """Change admin password after verifying old one."""
        import hashlib
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()
        try:
            self.cursor.execute(
                "SELECT id FROM admins WHERE admin_name=? AND password_hash=?",
                (admin_name, old_hash))
            row = self.cursor.fetchone()
            if not row:
                return False, "Incorrect current password"
            self.cursor.execute(
                "UPDATE admins SET password_hash=? WHERE admin_name=?",
                (new_hash, admin_name))
            self.conn.commit()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    # ── Classes ───────────────────────────────────────────────────────────────

    def get_classes(self, semester):
        self.cursor.execute(
            "SELECT * FROM classes WHERE semester=? ORDER BY slot",
            (semester,))
        return self.cursor.fetchall()

    def save_class(self, semester, slot, subject, teacher, t_start, t_end):
        try:
            self.cursor.execute("""
                INSERT INTO classes (semester,slot,subject_name,teacher_name,time_start,time_end)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(semester,slot) DO UPDATE SET
                    subject_name=excluded.subject_name,
                    teacher_name=excluded.teacher_name,
                    time_start=excluded.time_start,
                    time_end=excluded.time_end
            """, (semester, slot, subject, teacher, t_start, t_end))
            self.conn.commit()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def delete_class(self, semester, slot):
        try:
            self.cursor.execute(
                "DELETE FROM classes WHERE semester=? AND slot=?",
                (semester, slot))
            self.conn.commit()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def get_class_by_teacher(self, teacher_name, semester, subject):
        self.cursor.execute("""
            SELECT * FROM classes
            WHERE teacher_name=? AND semester=? AND subject_name=?
        """, (teacher_name, semester, subject))
        return self.cursor.fetchone()

    def get_all_teachers(self):
        self.cursor.execute(
            "SELECT DISTINCT teacher_name FROM classes ORDER BY teacher_name")
        return [r[0] for r in self.cursor.fetchall()]

    def get_subjects_for_teacher(self, teacher_name):
        self.cursor.execute("""
            SELECT subject_name, semester, time_start, time_end
            FROM classes WHERE teacher_name=?
            ORDER BY semester, subject_name
        """, (teacher_name,))
        return self.cursor.fetchall()

    def add_attendance_with_class(self, student_id, student_name, roll,
                                   semester, date, time, status,
                                   teacher_name, subject_name):
        try:
            self.cursor.execute("""
                INSERT INTO attendance
                    (student_id, student_name, roll_number, semester,
                     date, time, status, created_at)
                VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """, (student_id, student_name, roll, semester,
                  date, time, status))
            self.conn.commit()
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def get_student_by_id(self, student_id):
        try:
            self.cursor.execute("SELECT * FROM students WHERE id=?", (student_id,))
            return self.cursor.fetchone()
        except:
            return None

    def clean_old_records(self):
        try:
            one_year_ago = (datetime.now() - timedelta(days=210)).strftime("%Y-%m-%d")
            self.cursor.execute(
                'DELETE FROM attendance WHERE date < ?', (one_year_ago,))
            self.conn.commit()
        except Exception as e:
            print(f"Cleanup error: {e}")

    # ── Admin ─────────────────────────────────────────────────────────────────

    def get_admin_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM admins')
        return self.cursor.fetchone()[0]

    def add_admin(self, admin_name, phone_number, password):
        if self.get_admin_count() >= 2:
            return False, "Maximum 2 admins allowed"
        try:
            pw_hash = generate_password_hash(password)
            self.cursor.execute('''
                INSERT INTO admins (admin_name, phone_number, password_hash)
                VALUES (?, ?, ?)
            ''', (admin_name, phone_number, pw_hash))
            self.conn.commit()
            return True, "Admin created successfully"
        except sqlite3.IntegrityError:
            return False, "Admin name already exists"
        except Exception as e:
            return False, str(e)

    def verify_admin(self, admin_name, password):
        self.cursor.execute(
            'SELECT password_hash FROM admins WHERE admin_name = ?', (admin_name,))
        result = self.cursor.fetchone()
        return bool(result and check_password_hash(result[0], password))

    def admin_exists(self, admin_name):
        self.cursor.execute(
            'SELECT 1 FROM admins WHERE admin_name = ?', (admin_name,))
        return self.cursor.fetchone() is not None

    # ── Students ──────────────────────────────────────────────────────────────

    def add_student(self, name, father_name, roll_number, reg_number,
                    semester, image_path, auth_method='face'):
        try:
            self.cursor.execute('''
                INSERT INTO students
                    (name, father_name, roll_number, reg_number,
                     semester, image_path, auth_method)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, father_name, roll_number, reg_number,
                  semester, image_path, auth_method))
            self.conn.commit()
            return True, "Student registered successfully"
        except sqlite3.IntegrityError as e:
            if "roll_number" in str(e):
                return False, "Roll number already exists"
            elif "reg_number" in str(e):
                return False, "Registration number already exists"
            return False, "Student already exists"
        except Exception as e:
            return False, str(e)

    def get_student_auth_method(self, roll_number):
        self.cursor.execute(
            'SELECT auth_method FROM students WHERE roll_number = ?',
            (roll_number,))
        result = self.cursor.fetchone()
        return result[0] if result else 'face'

    def get_students_by_semester(self, semester):
        self.cursor.execute(
            'SELECT * FROM students WHERE semester = ? ORDER BY name',
            (semester,))
        return self.cursor.fetchall()

    def get_all_students(self):
        self.cursor.execute(
            'SELECT * FROM students ORDER BY semester, name')
        return self.cursor.fetchall()

    def get_student_by_roll(self, roll_number):
        self.cursor.execute(
            'SELECT * FROM students WHERE roll_number = ?', (roll_number,))
        return self.cursor.fetchone()

    def delete_student(self, student_id):
        try:
            self.cursor.execute(
                'DELETE FROM students WHERE id = ?', (student_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Delete error: {e}")
            return False

    def clear_semester(self, semester):
        try:
            self.cursor.execute(
                'DELETE FROM students WHERE semester = ?', (semester,))
            self.conn.commit()
            return True, f"Semester {semester} cleared successfully"
        except Exception as e:
            return False, str(e)

    # ── Attendance ────────────────────────────────────────────────────────────

    def mark_attendance(self, student_id, student_name, roll_number,
                        semester, date, time, status):
        try:
            self.cursor.execute('''
                SELECT id FROM attendance
                WHERE roll_number = ? AND date = ? AND status = 'Present'
            ''', (roll_number, date))
            if self.cursor.fetchone():
                return False, "Already marked present today"

            self.cursor.execute('''
                INSERT INTO attendance
                    (student_id, student_name, roll_number, semester,
                     date, time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (student_id, student_name, roll_number,
                  semester, date, time, status))
            self.conn.commit()
            return True, "Attendance marked"
        except Exception as e:
            return False, str(e)

    def mark_absent_students(self, date, present_rolls):
        try:
            students = self.get_all_students()
            for s in students:
                # students table: id(0), name(1), father_name(2), roll_number(3),
                #                 reg_number(4), semester(5), image_path(6), auth_method(7)
                student_id   = s[0]
                student_name = s[1]
                roll_number  = s[3]
                semester     = s[5]

                if roll_number in present_rolls:
                    continue
                self.cursor.execute('''
                    SELECT id FROM attendance
                    WHERE roll_number = ? AND date = ?
                ''', (roll_number, date))
                if self.cursor.fetchone():
                    continue
                self.cursor.execute('''
                    INSERT INTO attendance
                        (student_id, student_name, roll_number, semester,
                         date, time, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'Absent')
                ''', (student_id, student_name, roll_number,
                      semester, date, "N/A"))
            self.conn.commit()
        except Exception as e:
            print(f"mark_absent_students error: {e}")

    def get_attendance_by_date(self, date, semester=None):
        if semester:
            self.cursor.execute('''
                SELECT id, student_name, roll_number, semester,
                       date, time, status
                FROM attendance
                WHERE date = ? AND semester = ?
                ORDER BY time
            ''', (date, semester))
        else:
            self.cursor.execute('''
                SELECT id, student_name, roll_number, semester,
                       date, time, status
                FROM attendance
                WHERE date = ?
                ORDER BY time
            ''', (date,))
        return self.cursor.fetchall()

    def get_attendance_by_student(self, roll_number):
        self.cursor.execute('''
            SELECT id, student_name, roll_number, semester,
                   date, time, status
            FROM attendance
            WHERE roll_number = ?
            ORDER BY date DESC
        ''', (roll_number,))
        return self.cursor.fetchall()

    def get_all_attendance(self):
        self.cursor.execute('''
            SELECT id, student_name, roll_number, semester,
                   date, time, status
            FROM attendance
            ORDER BY date DESC, time DESC
        ''')
        return self.cursor.fetchall()

    def close(self):
        pass  # shared connection — do not close