import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')

def check_db():
    if not os.path.exists(DB_PATH):
        print("Database file not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- ROLES ---")
    cursor.execute("SELECT * FROM roles")
    for row in cursor.fetchall():
        print(dict(row))

    print("\n--- USERS ---")
    cursor.execute("""
        SELECT u.id, u.username, u.email, r.name as role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.id
    """)
    for row in cursor.fetchall():
        print(dict(row))

    conn.close()

if __name__ == "__main__":
    check_db()
