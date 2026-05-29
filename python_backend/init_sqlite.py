import sqlite3
import os
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')

def init_db():
    if os.path.exists(DB_PATH):
        print(f"Database already exists at {DB_PATH}. Skipping initialization to preserve data.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Roles
    cursor.execute("CREATE TABLE roles (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    cursor.executemany("INSERT INTO roles (name) VALUES (?)", [('admin',), ('hod',), ('guide',), ('student',)])

    # 2. Departments
    cursor.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, is_active INTEGER DEFAULT 1, description TEXT)")
    cursor.executemany("INSERT INTO departments (name, description) VALUES (?, ?)", 
                       [('Computer Science', 'CS Department'), ('Information Technology', 'IT Department')])

    # 3. Users
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            profile_photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)

    # 4. Role Tables
    cursor.execute("CREATE TABLE hods (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE, department_id INTEGER NOT NULL, plain_password TEXT, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (department_id) REFERENCES departments(id))")
    cursor.execute("CREATE TABLE guides (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE, department_id INTEGER NOT NULL, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (department_id) REFERENCES departments(id))")
    cursor.execute("CREATE TABLE students (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE, roll_number TEXT NOT NULL UNIQUE, department_id INTEGER NOT NULL, plain_password TEXT, academic_year TEXT, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (department_id) REFERENCES departments(id))")

    # 5. Teams & Projects
    cursor.execute("CREATE TABLE teams (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, guide_id INTEGER NULL, academic_year TEXT, is_solo BOOLEAN NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (guide_id) REFERENCES guides(id))")
    cursor.execute("CREATE TABLE team_members (id INTEGER PRIMARY KEY AUTOINCREMENT, team_id INTEGER NOT NULL, student_id INTEGER NOT NULL, is_leader BOOLEAN NOT NULL DEFAULT 0, FOREIGN KEY (team_id) REFERENCES teams(id), FOREIGN KEY (student_id) REFERENCES students(id), UNIQUE (student_id))")
    cursor.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL UNIQUE,
            title TEXT NOT NULL,
            abstract TEXT NOT NULL,
            tech_stack TEXT NOT NULL,
            github_link TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'pending',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (team_id) REFERENCES teams(id)
        )
    """)

    # 6. Evaluations & Logs
    cursor.execute("CREATE TABLE evaluations (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL UNIQUE, guide_id INTEGER NOT NULL, marks DECIMAL(5, 2), feedback TEXT, evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (project_id) REFERENCES projects(id), FOREIGN KEY (guide_id) REFERENCES guides(id))")
    cursor.execute("CREATE TABLE login_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, logout_time TIMESTAMP NULL, session_duration INTEGER NULL, FOREIGN KEY (user_id) REFERENCES users(id))")

    # Insert Admin
    hashed_pw = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor.execute("INSERT INTO users (role_id, username, email, password_hash) VALUES (1, 'Admin User', 'admin@portal.com', ?)", (hashed_pw,))

    conn.commit()
    conn.close()
    print(f"SQLite Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
