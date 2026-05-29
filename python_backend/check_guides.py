import sqlite3, os
DB_PATH = 'portal.db'
if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT g.id, u.username, u.email, g.department_id FROM guides g JOIN users u ON g.user_id = u.id")
    guides = [dict(row) for row in cursor.fetchall()]
    print(f"Total Guides: {len(guides)}")
    for g in guides:
        print(g)
    conn.close()
else:
    print("Database not found")
