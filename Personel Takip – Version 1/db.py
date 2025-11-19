import sqlite3

DB_NAME = "patron_app.db"


def get_conn():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # PERSONELLER
    c.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        hourly_rate REAL NOT NULL,
        start_date TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    # DEVAMSIZLIK
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        hours REAL DEFAULT 0,
        note TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    """)

    # AVANS TABLOSU (description dahil)
    c.execute("""
    CREATE TABLE IF NOT EXISTS advances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        installments INTEGER NOT NULL,
        remaining REAL NOT NULL,
        description TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    """)

    # MESAİ TABLOSU (description dahil)
    c.execute("""
    CREATE TABLE IF NOT EXISTS overtimes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        hours REAL NOT NULL,
        rate REAL NOT NULL,
        total REAL NOT NULL,
        description TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    """)

    # AYARLAR TABLOSU
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        daily_hours REAL NOT NULL,
        overtime_coef REAL NOT NULL,
        include_weekends INTEGER NOT NULL
    )
    """)

    # Varsayılan ayarları ekle (eğer yoksa)
    c.execute("SELECT COUNT(*) FROM settings")
    count = c.fetchone()[0]
    if count == 0:
        c.execute(
            "INSERT INTO settings (id, daily_hours, overtime_coef, include_weekends) VALUES (1, ?, ?, ?)",
            (10.0, 1.5, 1),  # 10 saat / 1.5 mesai / hafta sonu dahil
        )

    # Eski veritabanı için sütun ekleme denemeleri (varsa hata vermez)
    try:
        c.execute("ALTER TABLE advances ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE overtimes ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_settings():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT daily_hours, overtime_coef, include_weekends FROM settings WHERE id=1")
    row = c.fetchone()
    conn.close()
    if row is None:
        return 10.0, 1.5, 1
    return row  # (daily_hours, overtime_coef, include_weekends)


def update_settings(daily_hours, overtime_coef, include_weekends):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE settings SET daily_hours=?, overtime_coef=?, include_weekends=? WHERE id=1",
        (daily_hours, overtime_coef, include_weekends),
    )
    conn.commit()
    conn.close()


# ------------ EMPLOYEE CRUD ------------ #


def add_employee(name, rate, start_date, active):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO employees (name, hourly_rate, start_date, is_active)
    VALUES (?, ?, ?, ?)
    """, (name, rate, start_date, active))
    conn.commit()
    conn.close()


def update_employee(emp_id, name, rate, start_date, active):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    UPDATE employees
    SET name=?, hourly_rate=?, start_date=?, is_active=?
    WHERE id=?
    """, (name, rate, start_date, active, emp_id))
    conn.commit()
    conn.close()


def get_all_employees():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name, hourly_rate, start_date, is_active FROM employees")
    rows = c.fetchall()
    conn.close()
    return rows


def get_active_employees():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, name, hourly_rate, start_date
        FROM employees
        WHERE is_active=1
        ORDER BY name
    """)
    rows = c.fetchall()
    conn.close()
    return rows


# ------------ ATTENDANCE ------------ #


def add_attendance(emp_id, date_str, type_code, hours, note):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO attendance_logs (employee_id, date, type, hours, note)
    VALUES (?, ?, ?, ?, ?)
    """, (emp_id, date_str, type_code, hours, note))
    conn.commit()
    conn.close()


def get_attendance_for_month(emp_id, start_date, end_date):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT date, type, hours FROM attendance_logs
    WHERE employee_id=? AND date>=? AND date<?
    """, (emp_id, start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return rows


def update_attendance(att_id, employee_id, date_str, type_code, hours, note):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE attendance_logs
        SET employee_id=?, date=?, type=?, hours=?, note=?
        WHERE id=?
    """, (employee_id, date_str, type_code, hours, note, att_id))
    conn.commit()
    conn.close()


def delete_attendance(att_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM attendance_logs WHERE id=?", (att_id,))
    conn.commit()
    conn.close()


# ------------ ADVANCE ------------ #


def add_advance(emp_id, date_str, amount, installments, description=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO advances (employee_id, date, amount, installments, remaining, description)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (emp_id, date_str, amount, installments, amount, description))
    conn.commit()
    conn.close()


def get_advances(emp_id):
    """Maaş hesaplamasında kullanılan sade liste (açıklamasız)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT id, date, amount, installments, remaining
    FROM advances
    WHERE employee_id=? AND remaining>0
    """, (emp_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def update_advance_remaining(adv_id, new_remaining):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE advances SET remaining=? WHERE id=?", (new_remaining, adv_id))
    conn.commit()
    conn.close()


def update_advance(adv_id, employee_id, date_str, amount, installments, remaining, description):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE advances
        SET employee_id=?, date=?, amount=?, installments=?, remaining=?, description=?
        WHERE id=?
    """, (employee_id, date_str, amount, installments, remaining, description, adv_id))
    conn.commit()
    conn.close()


def delete_advance(adv_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM advances WHERE id=?", (adv_id,))
    conn.commit()
    conn.close()


def get_advance_by_id(adv_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, employee_id, date, amount, installments, remaining, description
        FROM advances
        WHERE id=?
    """, (adv_id,))
    row = c.fetchone()
    conn.close()
    return row


# ------------ OVERTIME ------------ #


def add_overtime(emp_id, date_str, hours, rate, total, description=""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT INTO overtimes (employee_id, date, hours, rate, total, description)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (emp_id, date_str, hours, rate, total, description))
    conn.commit()
    conn.close()


def get_overtime_for_month(emp_id, start_date, end_date):
    """Maaş hesaplaması için; açıklamaya ihtiyaç yok."""
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT date, hours, rate, total
    FROM overtimes
    WHERE employee_id=? AND date>=? AND date<?
    """, (emp_id, start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return rows


def update_overtime(ot_id, employee_id, date_str, hours, rate, total, description):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE overtimes
        SET employee_id=?, date=?, hours=?, rate=?, total=?, description=?
        WHERE id=?
    """, (employee_id, date_str, hours, rate, total, description, ot_id))
    conn.commit()
    conn.close()


def delete_overtime(ot_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM overtimes WHERE id=?", (ot_id,))
    conn.commit()
    conn.close()
