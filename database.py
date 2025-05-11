# database.py
import sqlite3
from datetime import datetime
import pandas as pd
from aiogram.types import FSInputFile


def init_db():
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            amount REAL,
            category TEXT,
            date TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            language TEXT DEFAULT 'ru-RU',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()
    
def set_user_language(user_id, language):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_settings (user_id, language)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET language = ?
    """, (user_id, language, language))
    conn.commit()
    conn.close()
    
def get_user_language(user_id):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT language FROM user_settings WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None    

def calculate_balance(user_id):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN LOWER(type) = 'доход' THEN amount ELSE -amount END) AS balance
        FROM transactions WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    conn.close()

    return round(result[0], 0) if result[0] is not None else 0

def calculate_balance_by_category(user_id):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, type, SUM(amount) 
        FROM transactions 
        WHERE user_id = ? 
        GROUP BY category, type
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()

    categories = {}

    for category, trans_type, amount in rows:
        if category not in categories:
            categories[category] = 0
        if trans_type == "доход":
            categories[category] += amount
        else:
            categories[category] -= amount

    return categories

def add_user(user_id, name):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

def add_transaction(user_id, data):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (user_id, type, amount, category, date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("тип"),       # ← Используйте ключи на русском
        float(data.get("сумма", 0)),
        data.get("категория"),
        datetime.now().strftime("%Y-%m-%d")
    ))
    conn.commit()
    conn.close()

def get_transactions_by_period(user_id, period="month"):
    today = datetime.today()
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()

    if period == "week":
        query = """
            SELECT * FROM transactions
            WHERE user_id = ? AND date >= date('now', '-7 days')
        """
    else:  # month
        query = """
            SELECT * FROM transactions
            WHERE user_id = ? AND strftime('%Y-%m', date) = ?
        """
        args = (user_id, today.strftime("%Y-%m"))
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_transaction_history(user_id, limit=10):
    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT type, amount, category, date 
        FROM transactions 
        WHERE user_id = ? 
        ORDER BY date DESC 
        LIMIT ?
    """, (user_id, limit))
    
    rows = cursor.fetchall()
    conn.close()

    return rows

def export_to_excel(user_id):
    conn = sqlite3.connect("budget.db")
    query = """
        SELECT date, type, amount, category 
        FROM transactions 
        WHERE user_id = ?
        ORDER BY date DESC
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()

    # Форматируем данные
    df['amount'] = df.apply(lambda row: f"+{row['amount']}" if row['type'] == 'доход' else f"-{abs(row['amount'])}", axis=1)
    
    # Создаём Excel-файл
    filename = f"{user_id}_transactions.xlsx"
    df.to_excel(filename, index=False, engine="openpyxl")
    return filename
    conn = sqlite3.connect("budget.db")
    df = pd.read_sql_query(f"SELECT * FROM transactions WHERE user_id={user_id}", conn)
    filename = f"{user_id}_transactions.xlsx"
    df.to_excel(filename, index=False)
    return filename