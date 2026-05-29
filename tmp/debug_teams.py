import sqlite3
import os

DB_PATH = 'C:/Users/user/Desktop/ONLINE PROJECT SUBMISSION PORTAL/python_backend/portal.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Depid 3 was MCA
dept_id = 3
query = """
    SELECT t.id, t.name, t.is_solo, t.guide_id, t.academic_year, p.title as project_title, p.status 
    FROM teams t 
    JOIN team_members tm ON t.id = tm.team_id
    JOIN students s ON tm.student_id = s.id
    LEFT JOIN projects p ON p.team_id = t.id
    WHERE s.department_id = ?
    GROUP BY t.id
"""
c.execute(query, (dept_id,))
rows = c.fetchall()
print(f"FOR DEPT {dept_id}: Found {len(rows)} teams")
for row in rows:
    print(dict(row))

conn.close()
