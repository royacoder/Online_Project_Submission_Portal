import sqlite3, os
DB_PATH = 'portal.db'
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT u.username, h.department_id FROM hods h JOIN users u ON h.user_id = u.id")
    hods = [dict(row) for row in cursor.fetchall()]
    print(f"Total HODs: {len(hods)}")
    for h in hods:
        print(h)
    conn.close()
