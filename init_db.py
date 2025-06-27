import sqlite3
import os
from datetime import datetime

# === Database Path Setup ===
DB_PATH = os.path.join('db', 'library.db')

if not os.path.exists(DB_PATH):
    # ✅ Only create database if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # === Utility Function to Add Column Safely ===
    def add_column_safely(table, column_name, column_type):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type};")
            print(f"✅ Column '{column_name}' added to '{table}'.")
        except sqlite3.OperationalError as e:
            if f"duplicate column name: {column_name}" in str(e).lower():
                print(f"ℹ️ Column '{column_name}' already exists in '{table}'.")
            else:
                print(f"⚠️ Error adding column '{column_name}' to '{table}': {e}")

    # === Step 1: Create students table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        year INTEGER NOT NULL,
        gender TEXT CHECK(gender IN ('male', 'female', 'other')) DEFAULT 'male',
        phone TEXT,
        email TEXT,
        status TEXT CHECK(status IN ('active', 'inactive')) DEFAULT 'active',
        photo TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("✅ 'students' table created.")

    # === Step 2: Add necessary columns to students ===
    student_columns = {
        "address": "TEXT",
        "father_name": "TEXT",
        "education": "TEXT",
        "exam": "TEXT",
        "school_10": "TEXT",
        "percent_10": "TEXT",
        "school_12": "TEXT",
        "percent_12": "TEXT",
        "college_grad": "TEXT",
        "percent_grad": "TEXT",
        "fees_status": "TEXT DEFAULT 'unpaid'",
        "username": "TEXT",
        "password": "TEXT",
        "admission": "TEXT",
        "table_number": "TEXT",
        "library_timing": "TEXT",
        "fees_amount": "TEXT",
        "transaction_id": "TEXT",
        "month": "TEXT",
        "approved": "INTEGER DEFAULT 0",
        "is_deleted": "INTEGER DEFAULT 0"
    }
    for col, col_type in student_columns.items():
        add_column_safely("students", col, col_type)

    # === Step 3: Create payment_settings table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT
    );
    """)
    add_column_safely("payment_settings", "phonepe_id", "TEXT")
    add_column_safely("payment_settings", "qr_code_path", "TEXT")
    print("✅ 'payment_settings' table ready.")

    # === Step 4: Create expenses table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL,
        category TEXT,
        source TEXT,
        description TEXT,
        date TEXT
    );
    """)
    add_column_safely("expenses", "is_deleted", "INTEGER DEFAULT 0")
    print("✅ 'expenses' table created.")

    # === Step 5: Create settings table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total_seats INTEGER DEFAULT 60,
        library_name TEXT,
        library_address TEXT,
        library_phone TEXT,
        opening_hours TEXT,
        about TEXT
    );
    """)
    cur.execute("""
    INSERT INTO settings (total_seats)
    SELECT 60 WHERE NOT EXISTS (SELECT 1 FROM settings);
    """)
    print("✅ 'settings' table created and seeded if empty.")

    # === Step 6: Create donations table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS donations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        item TEXT NOT NULL,
        description TEXT,
        photo TEXT
    );
    """)
    add_column_safely("donations", "is_deleted", "INTEGER DEFAULT 0")
    print("✅ 'donations' table created.")

    # === Step 7: Create authorities table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS authorities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        photo TEXT
    );
    """)
    add_column_safely("authorities", "is_deleted", "INTEGER DEFAULT 0")
    print("✅ 'authorities' table created.")

    # === Step 8: Create feedback table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        date TEXT
    );
    """)
    print("✅ 'feedback' table created.")

    # === Step 9: Create fees_settings table ===
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fees_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phonepe_number TEXT,
        qr_image TEXT
    );
    """)
    print("✅ 'fees_settings' table created.")

    # === Step 10: Fix or create notices table ===
    cur.execute("PRAGMA table_info(notices);")
    columns = [col[1] for col in cur.fetchall()]

    if 'message' in columns:
        print("⚠️ Fixing 'notices' table to remove 'message' and use 'content'...")

        cur.execute("ALTER TABLE notices RENAME TO old_notices;")
        cur.execute("""
        CREATE TABLE notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        cur.execute("""
        INSERT INTO notices (id, title, content, created_at)
        SELECT id, title, message, created_at FROM old_notices;
        """)
        cur.execute("DROP TABLE old_notices;")

        print("✅ 'notices' table fixed and cleaned (message removed).")

    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """)
        print("✅ 'notices' table verified or created (no message column).")

    # === Finish ===
    conn.commit()
    conn.close()
    print("🎉 All tables and columns created/verified successfully.")

else:
    print("ℹ️ Database already exists. Skipping creation.")
