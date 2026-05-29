import os
import time
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_session import Session
import bcrypt
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_secret_key_12345'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend/uploads/project_files/')
app.config['UPLOAD_PROFILE_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend/uploads/profile_photos/')
app.config['UPLOAD_SCREENSHOT_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend/uploads/project_screenshots/')

# Ensure folders exist
for folder in [app.config['UPLOAD_FOLDER'], app.config['UPLOAD_PROFILE_FOLDER'], app.config['UPLOAD_SCREENSHOT_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)
CORS(app, supports_credentials=True)

# Session configuration
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), 'flask_session_data')
Session(app)

# SQLite Configuration                         connection string 27-37
DB_PATH = os.path.join(os.path.dirname(__file__), 'portal.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode = WAL')
    conn.execute('PRAGMA synchronous = NORMAL')
    conn.execute('PRAGMA cache_size = -2000') # 2MB cache
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    return conn

def migrate_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Migration checks - run only once at startup
    try:
        cursor.execute("SELECT is_active FROM users LIMIT 1")
    except:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    
    try:
        cursor.execute("SELECT profile_photo FROM users LIMIT 1")
    except:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
    
    try:
        cursor.execute("SELECT academic_year FROM students LIMIT 1")
    except:
        cursor.execute("ALTER TABLE students ADD COLUMN academic_year TEXT")
        
    try:
        cursor.execute("SELECT academic_year FROM teams LIMIT 1")
    except:
        cursor.execute("ALTER TABLE teams ADD COLUMN academic_year TEXT")
        
    try:
        cursor.execute("SELECT is_active FROM departments LIMIT 1")
    except:
        cursor.execute("ALTER TABLE departments ADD COLUMN is_active INTEGER DEFAULT 1")
    
    # Sections Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            coordinator_id INTEGER NULL,
            FOREIGN KEY (department_id) REFERENCES departments(id),
            FOREIGN KEY (coordinator_id) REFERENCES guides(id)
        )
    """)
    
    try:
        cursor.execute("SELECT section_id FROM students LIMIT 1")
    except:
        cursor.execute("ALTER TABLE students ADD COLUMN section_id INTEGER REFERENCES sections(id)")
        
    # Notifications Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            sender_id INTEGER,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    
    try:
        cursor.execute("UPDATE users SET profile_photo = REPLACE(profile_photo, 'profile_photos/', '') WHERE profile_photo LIKE 'profile_photos/%'")
    except:
        pass
        


    # Add Clerk role if not exists
    cursor.execute("SELECT id FROM roles WHERE name = 'clerk'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO roles (name) VALUES ('clerk')")
        


    # Ensure semester column exists
    try:
        cursor.execute("SELECT semester FROM projects LIMIT 1")
    except:
        cursor.execute("ALTER TABLE projects ADD COLUMN semester TEXT")
        
    # Ensure screenshot_path column exists
    try:
        cursor.execute("SELECT screenshot_path FROM projects LIMIT 1")
    except:
        cursor.execute("ALTER TABLE projects ADD COLUMN screenshot_path TEXT")
    
    # Ensure website_link column exists
    try:
        cursor.execute("SELECT website_link FROM projects LIMIT 1")
    except:
        cursor.execute("ALTER TABLE projects ADD COLUMN website_link TEXT")
    
    # Set default semester for existing data
    cursor.execute("UPDATE projects SET semester = 'Semester 1' WHERE semester IS NULL OR semester = ''")

    # Migration for renamed columns: edit_request -> resubmission_request, edit_reason -> resubmission_reason
    # 1. Check if resubmission_request already exists
    try:
        cursor.execute("SELECT resubmission_request FROM projects LIMIT 1")
    except:
        # Check if old column exists to rename it
        try:
            cursor.execute("SELECT edit_request FROM projects LIMIT 1")
            cursor.execute("ALTER TABLE projects RENAME COLUMN edit_request TO resubmission_request")
        except:
            # Neither exists, add the new one
            cursor.execute("ALTER TABLE projects ADD COLUMN resubmission_request TEXT")

    # 2. Check if resubmission_reason already exists
    try:
        cursor.execute("SELECT resubmission_reason FROM projects LIMIT 1")
    except:
        # Check if old column exists to rename it
        try:
            cursor.execute("SELECT edit_reason FROM projects LIMIT 1")
            cursor.execute("ALTER TABLE projects RENAME COLUMN edit_reason TO resubmission_reason")
        except:
            # Neither exists, add the new one
            cursor.execute("ALTER TABLE projects ADD COLUMN resubmission_reason TEXT")

    # performance Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_user ON students(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_students_dept ON students(department_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teams_guide ON teams(guide_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_team_members_student ON team_members(student_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_team ON projects(team_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_project ON evaluations(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sections_dept ON sections(department_id)")

    # Project Screenshots Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_screenshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            screenshot_path TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screenshots_project ON project_screenshots(project_id)")

    # Data Migration: Move existing single screenshots to the new table
    cursor.execute("SELECT id, screenshot_path FROM projects WHERE screenshot_path IS NOT NULL AND screenshot_path != ''")
    projects_with_ss = cursor.fetchall()
    for p in projects_with_ss:
        # Use integer indices (0 for id, 1 for screenshot_path) because migrate_db uses standard connection
        project_id = p[0]
        screenshot_path = p[1]
        cursor.execute("SELECT COUNT(*) as count FROM project_screenshots WHERE project_id = ? AND screenshot_path = ?", (project_id, screenshot_path))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO project_screenshots (project_id, screenshot_path) VALUES (?, ?)", (project_id, screenshot_path))
        
    conn.commit()
    conn.close()

# Run migrations at startup
migrate_db()

@app.route('/api', methods=['GET', 'POST'])
def api_router():
    action = request.args.get('action')
    if not action:
        return jsonify({'success': False, 'message': 'Invalid action'}), 400

    # Authentication Routes
    if action == 'login':
        return login()
    elif action == 'logout':
        return logout()
    elif action == 'getSession':
        return get_session()
    elif action == 'registerStudent':
        return register_student()
    elif action == 'resetPassword':
        return reset_password()
    elif action == 'getDepartments':
        return get_departments()
    
    # Team Routes
    elif action == 'createTeam':
        return create_team()
    elif action == 'getStudentTeam':
        return get_student_team()
    elif action == 'getAvailableStudents':
        return get_available_students()
    
    # Project Routes
    elif action == 'submitProject':
        return submit_project()
    elif action == 'getStudentProject':
        return get_student_project()
    elif action == 'getGuideProjects':
        return get_guide_projects()
    elif action == 'updateProjectStatus':
        return update_project_status()
    elif action == 'requestEditOption':
        return request_resubmission_option()
    elif action == 'getNotifications':
        return get_notifications()
    elif action == 'markNotificationRead':
        return mark_notification_read()
    
    # Evaluation Routes
    elif action == 'evaluateProject':
        return evaluate_project()
    elif action == 'getEvaluation':
        return get_evaluation()
    elif action == 'getGuideTeams':
        return get_guide_teams()
    
    # Admin Routes
    elif action == 'getAdminStats':
        return get_admin_stats()
    elif action == 'getAllUsers':
        return get_all_users()
    elif action == 'createDepartment':
        return create_department()
    elif action == 'createHod':
        return create_hod()
    elif action == 'createStudentByAdmin':
        return create_student_by_admin()
    elif action == 'toggleDepartmentStatus':
        return toggle_department_status()
    elif action == 'changeHod':
        return change_hod()
    elif action == 'getTeachingStaffForDept':
        return get_teaching_staff_for_dept()
    elif action == 'assignExistingStaffAsHod':
        return assign_existing_staff_as_hod()
    elif action == 'getAdminWatchDetails':
        return get_admin_watch_details()
    elif action == 'getAdminProjectReport':
        return get_admin_project_report()
    elif action == 'getHodProjectReport':
        return get_hod_project_report()
    elif action == 'getGuideProjectReport':
        return get_guide_project_report()
    
    # HOD Routes and Shared
    elif action == 'createStudentByHod':
        return create_student_by_hod()
    elif action == 'getHodStudents':
        return get_hod_students()
    elif action == 'getHodTeams':
        return get_hod_teams()
    elif action == 'getGuides':
        return get_guides()
    elif action == 'createGuide':
        return create_guide()
    elif action == 'assignGuide':
        return assign_guide()
    elif action == 'getTeamDetails':
        return get_team_details()
    elif action == 'deleteGuide':
        return delete_guide()
    elif action == 'deleteStudent':
        return delete_student()
    elif action == 'deleteTeam':
        return delete_team()
    elif action == 'deleteUser':
        return toggle_user_status()
    elif action == 'toggleUserStatus':
        return toggle_user_status()
    elif action == 'changeUserEmail':
        return change_user_email()
    elif action == 'deleteHod':
        return delete_hod()
    elif action == 'getHodStats':
        return get_hod_stats()
    elif action == 'getSections':
        return get_sections()
    elif action == 'createSection':
        return create_section()
    elif action == 'assignGuideToSection':
        return assign_guide_to_section()
    elif action == 'assignSection':
        return assign_section()
    elif action == 'assignGuideToStudentTeam':
        return assign_guide_to_student_team()
    elif action == 'getUserProfile':
        return get_user_profile()
    elif action == 'uploadProfilePhoto':
        return upload_profile_photo()
    
    # Clerk Routes
    elif action == 'getClerkStats':
        return get_clerk_stats()
    elif action == 'createStudentByClerk':
        return create_student_by_clerk()
    
    # Admin Clerk Management
    elif action == 'createClerk':
        return create_clerk_by_admin()
    elif action == 'getClerks':
        return get_clerks()
    
    # Public Routes
    elif action == 'getApprovedProjects':
        return get_approved_projects()
    elif action == 'getProjectById':
        return get_project_by_id()
    
    return jsonify({'success': False, 'message': f"Action '{action}' not implemented"}), 404


def login():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT u.*, r.name as role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.id 
        WHERE u.email = ?
    """
    cursor.execute(query, (email,))
    user = cursor.fetchone()
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        if user['is_active'] == 0:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Account is inactive. Please contact administrator.'})

        session['user_id'] = user['id']
        session['email'] = user['email']
        session['username'] = user['username']
        session['role_name'] = user['role_name']
        
        # Log login
        cursor.execute("INSERT INTO login_logs (user_id) VALUES (?)", (user['id'],))
        conn.commit()
        
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'role': user['role_name'], 'message': 'Login successful'})
    
    cursor.close()
    conn.close()
    return jsonify({'success': False, 'message': 'Invalid credentials'})

def reset_password():
    data = request.form
    email = data.get('email')
    new_password = data.get('new_password')
    
    if not email or not new_password:
        return jsonify({'success': False, 'message': 'Email and new password are required'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if not user:
        cursor.close()
        conn.close()
        return jsonify({'success': False, 'message': 'No account found with this email'})
        
    hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, user['id']))
        cursor.execute("UPDATE students SET plain_password = ? WHERE user_id = ?", (new_password, user['id']))
        cursor.execute("UPDATE hods SET plain_password = ? WHERE user_id = ?", (new_password, user['id']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Password reset successful!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def logout():
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Find last login and update logout time
        cursor.execute("""
            UPDATE login_logs 
            SET logout_time = CURRENT_TIMESTAMP, 
                session_duration = strftime('%s', 'now') - strftime('%s', login_time)
            WHERE user_id = ? AND logout_time IS NULL 
            ORDER BY login_time DESC LIMIT 1
        """, (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
    
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

def get_session():
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT profile_photo FROM users WHERE id = ?", (session['user_id'],))
        user_row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'role': session['role_name'],
                'profile_photo': user_row['profile_photo'] if user_row else None
            }
        })
    return jsonify({'success': False})

def get_departments():
    only_active = request.args.get('only_active') == 'true'
    conn = get_db_connection()
    cursor = conn.cursor()
    if only_active:
        cursor.execute("SELECT * FROM departments WHERE is_active = 1")
    else:
        cursor.execute("SELECT * FROM departments")
    depts = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'data': depts})

def register_student():
    """Disabled for public; Clerk or HOD must add students now."""
    return jsonify({
        'success': False, 
        'message': 'Direct registration is disabled. Please contact your department Clerk or HOD to create an account.'
    }), 403

def register_student_internal(): # Renamed the original for internal use if needed, but not exposed
    data = request.form
    name = data.get('name')
    email = data.get('email')
    roll = data.get('roll')
    department_id = data.get('department')
    password = data.get('password')
    academic_year = data.get('academic_year')
    is_solo = data.get('is_solo') == 'true'
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get role ID for student
        cursor.execute("SELECT id FROM roles WHERE name = 'student'")
        role = cursor.fetchone()
        
        # Insert user
        cursor.execute(
            "INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (role['id'], name, email, hashed_pw)
        )
        user_id = cursor.lastrowid
        
        # Insert student record
        cursor.execute(
            "INSERT INTO students (user_id, roll_number, department_id, plain_password, academic_year) VALUES (?, ?, ?, ?, ?)",
            (user_id, roll, department_id, password, academic_year)
        )
        student_id = cursor.lastrowid

        if is_solo:
            # Create a solo team immediately
            team_name = f"Solo - {name}"
            # Ensure unique team name
            cursor.execute("SELECT COUNT(*) as count FROM teams WHERE name = ?", (team_name,))
            if cursor.fetchone()['count'] > 0:
                team_name = f"Solo - {name} ({roll})"
            
            cursor.execute("INSERT INTO teams (name, is_solo, academic_year) VALUES (?, ?, ?)", (team_name, 1, academic_year))
            team_id = cursor.lastrowid
            cursor.execute("INSERT INTO team_members (team_id, student_id, is_leader) VALUES (?, ?, ?)", (team_id, student_id, 1))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Registered successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_team():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    team_name = data.get('team_name')
    partner_id = data.get('partner_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get student info for logged in user
        cursor.execute("SELECT id, academic_year, section_id FROM students WHERE user_id = ?", (session['user_id'],))
        student = cursor.fetchone()
        
        if not student or not student['section_id']:
            return jsonify({'success': False, 'message': 'You cannot create a team until the HOD assigns you to a section.'})
            
        leader_id = student['id']
        academic_year = student['academic_year']
        section_id = student['section_id']
        
        is_solo = 1 if not partner_id else 0
        
        cursor.execute("INSERT INTO teams (name, is_solo, academic_year) VALUES (?, ?, ?)", (team_name, is_solo, academic_year))
        team_id = cursor.lastrowid
        
        # Insert leader
        cursor.execute("INSERT INTO team_members (team_id, student_id, is_leader) VALUES (?, ?, ?)", (team_id, leader_id, 1))
        
        if not is_solo:
            # Check if partner is in the same section
            cursor.execute("SELECT section_id FROM students WHERE id = ?", (partner_id,))
            p_student = cursor.fetchone()
            if not p_student or p_student['section_id'] != section_id:
                return jsonify({'success': False, 'message': 'You can only team up with students from your own section.'})
                
            # Insert partner
            cursor.execute("INSERT INTO team_members (team_id, student_id, is_leader) VALUES (?, ?, ?)", (team_id, partner_id, 0))
            
        conn.commit()
        return jsonify({'success': True, 'message': 'Team created!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_student_team():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student = cursor.fetchone()
    
    if student:
        cursor.execute("""
            SELECT t.*, tm.is_leader 
            FROM teams t 
            JOIN team_members tm ON t.id = tm.team_id 
            WHERE tm.student_id = ?
        """, (student['id'],))
        team = cursor.fetchone()
        
        if team:
            cursor.execute("""
                SELECT s.roll_number, u.username, tm.is_leader 
                FROM team_members tm 
                JOIN students s ON tm.student_id = s.id 
                JOIN users u ON s.user_id = u.id 
                WHERE tm.team_id = ?
            """, (team['id'],))
            members = [dict(row) for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'team': dict(team), 'members': members})
            
    cursor.close()
    conn.close()
    return jsonify({'success': False, 'message': 'No team found.'})

def get_available_students():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT department_id, section_id FROM students WHERE user_id = ?", (session['user_id'],))
    student = cursor.fetchone()
    
    if student:
        if not student['section_id']:
            return jsonify({'success': False, 'message': 'Section not assigned yet. You cannot form a team.', 'students': []})
            
        cursor.execute("""
            SELECT s.id, u.username, s.roll_number 
            FROM students s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.department_id = ? 
            AND s.section_id = ?
            AND s.user_id != ?
            AND s.id NOT IN (SELECT student_id FROM team_members)
        """, (student['department_id'], student['section_id'], session['user_id']))
        available = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'students': available})
    
    cursor.close()
    conn.close()
    return jsonify({'success': False})

def submit_project():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    title = data.get('title')
    abstract = data.get('abstract')
    tech_stack = data.get('tech_stack')
    github = data.get('github')
    semester = data.get('semester', '')
    website_link = data.get('website_link', '').strip()
    
    # Validate website_link if provided
    if website_link and not (website_link.startswith('http://') or website_link.startswith('https://')):
        return jsonify({'success': False, 'message': 'Website link must start with http:// or https://'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
        student = cursor.fetchone()
        
        cursor.execute("SELECT team_id FROM team_members WHERE student_id = ?", (student['id'],))
        tm = cursor.fetchone()
        
        if not tm:
            return jsonify({'success': False, 'message': 'No team found.'})
            
        team_id = tm['team_id']
        
        cursor.execute("SELECT guide_id FROM teams WHERE id = ?", (team_id,))
        team = cursor.fetchone()
        if not team or not team['guide_id']:
            return jsonify({'success': False, 'message': 'You cannot submit a project until a Guide has been assigned to your team.'})
        
        file_path = None
        if 'project_file' in request.files:
            file = request.files['project_file']
            if file.filename != '':
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filename = str(int(time.time())) + "_" + secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                file_path = filename

        # Multiple Screenshots Handling
        new_screenshots = []
        screenshot_files = request.files.getlist('screenshot_files')
        
        if screenshot_files:
            if len(screenshot_files) > 4:
                return jsonify({'success': False, 'message': 'You can upload a maximum of 4 screenshots only'})

            for s_file in screenshot_files:
                if s_file.filename != '':
                    allowed_extensions = {'png', 'jpg', 'jpeg'}
                    ext = s_file.filename.rsplit('.', 1)[1].lower() if '.' in s_file.filename else ''
                    if ext not in allowed_extensions:
                        return jsonify({'success': False, 'message': f'Invalid format for {s_file.filename}. Only JPG, JPEG, PNG allowed.'})
                    
                    s_file.seek(0, os.SEEK_END)
                    size = s_file.tell()
                    s_file.seek(0)
                    if size > 2 * 1024 * 1024: # 2MB limit per image
                        return jsonify({'success': False, 'message': f'Screenshot {s_file.filename} exceeds 2MB limit.'})

                    if not os.path.exists(app.config['UPLOAD_SCREENSHOT_FOLDER']):
                        os.makedirs(app.config['UPLOAD_SCREENSHOT_FOLDER'], exist_ok=True)
                    
                    s_filename = str(int(time.time())) + "_" + str(len(new_screenshots)) + "_ss_" + secure_filename(s_file.filename)
                    s_file.save(os.path.join(app.config['UPLOAD_SCREENSHOT_FOLDER'], s_filename))
                    new_screenshots.append(s_filename)

        cursor.execute("SELECT id, screenshot_path FROM projects WHERE team_id = ?", (team_id,))
        existing_proj = cursor.fetchone()
        
        # Check if we have at least one screenshot (either new or existing)
        if not new_screenshots:
            cursor.execute("SELECT COUNT(*) as count FROM project_screenshots WHERE project_id = (SELECT id FROM projects WHERE team_id = ?)", (team_id,))
            ss_count = cursor.fetchone()['count']
            if ss_count == 0:
                return jsonify({'success': False, 'message': 'At least one website preview screenshot is required.'})

        # Insert or Update Project
        cursor.execute("""
            INSERT INTO projects (team_id, title, abstract, tech_stack, github_link, file_path, semester, website_link) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(team_id) DO UPDATE SET
            title=excluded.title, abstract=excluded.abstract, tech_stack=excluded.tech_stack, 
            github_link=excluded.github_link, file_path=COALESCE(excluded.file_path, projects.file_path),
            semester=excluded.semester,
            website_link=excluded.website_link,
            status='pending'
        """, (team_id, title, abstract, tech_stack, github, file_path, semester, website_link))
        
        project_id = existing_proj['id'] if existing_proj else cursor.lastrowid
        
        # If new screenshots are uploaded, we might want to replace existing ones or append.
        # Requirement says: "Store multiple screenshots linked to the project". 
        # Usually, during submission/update, we replace the set.
        if new_screenshots:
            cursor.execute("DELETE FROM project_screenshots WHERE project_id = ?", (project_id,))
            for ss in new_screenshots:
                cursor.execute("INSERT INTO project_screenshots (project_id, screenshot_path) VALUES (?, ?)", (project_id, ss))
            # Also update the legacy column for backward compatibility with simple queries
            cursor.execute("UPDATE projects SET screenshot_path = ? WHERE id = ?", (new_screenshots[0], project_id))

        # Notify Guide
        if team['guide_id']:
            cursor.execute("SELECT user_id FROM guides WHERE id = ?", (team['guide_id'],))
            g_user = cursor.fetchone()
            if g_user:
                cursor.execute("INSERT INTO notifications (user_id, sender_id, title, message) VALUES (?, ?, ?, ?)",
                    (g_user['user_id'], session['user_id'], 'Project Submitted', f'A project titled "{title}" has been submitted for your review.'))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Project submitted!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_student_project():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM students WHERE user_id = ?", (session['user_id'],))
    student = cursor.fetchone()
    
    cursor.execute("SELECT team_id FROM team_members WHERE student_id = ?", (student['id'],))
    tm = cursor.fetchone()
    
    if tm:
        cursor.execute("""
            SELECT p.*, g.username as guide_name, e.marks, e.feedback 
            FROM projects p 
            JOIN teams t ON p.team_id = t.id 
            LEFT JOIN guides lg ON t.guide_id = lg.id
            LEFT JOIN users g ON lg.user_id = g.id
            LEFT JOIN evaluations e ON p.id = e.project_id
            WHERE p.team_id = ?
        """, (tm['team_id'],))
        proj = cursor.fetchone()
        
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'project': dict(proj) if proj else None})
    
    cursor.close()
    conn.close()
    return jsonify({'success': False})

def get_guide_projects():
    if 'user_id' not in session or session.get('role_name') != 'guide':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM guides WHERE user_id = ?", (session['user_id'],))
    guide = cursor.fetchone()
    
    cursor.execute("""
        SELECT p.*, t.name as team_name, t.id as team_id 
        FROM projects p 
        JOIN teams t ON p.team_id = t.id 
        WHERE t.guide_id = ?
    """, (guide['id'],))
    projects = [dict(row) for row in cursor.fetchall()]
    
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'projects': projects})

def update_project_status():
    role = session.get('role_name')
    if 'user_id' not in session or role not in ['guide', 'admin', 'hod']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.form
    project_id = data.get('project_id')
    status = data.get('status')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        proj = cursor.fetchone()
        if not proj:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
            
        current_status = proj['status']
        
        if role == 'guide':
            if status == 'approved':
                cursor.execute("SELECT id FROM evaluations WHERE project_id = ?", (project_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'message': 'Cannot approve project without giving marks and feedback first.'})
            elif status != 'approved':
                if current_status == 'approved':
                    return jsonify({'success': False, 'message': 'Project is already approved. Only HOD can give Resubmission options now.'})
            
            # Notify students of the new status
            cursor.execute("""
                SELECT s.user_id, p.title 
                FROM projects p 
                JOIN teams t ON p.team_id = t.id 
                JOIN team_members tm ON t.id = tm.team_id
                JOIN students s ON tm.student_id = s.id
                WHERE p.id = ?
            """, (project_id,))
            team_members = cursor.fetchall()
            for row in team_members:
                cursor.execute("INSERT INTO notifications (user_id, sender_id, title, message) VALUES (?, ?, ?, ?)",
                    (row['user_id'], session['user_id'], f'Project {status.capitalize()}', f'Your project "{row["title"]}" has been marked as {status} by your guide.'))

        elif role == 'hod':
            if status not in ['resubmit']:
                 return jsonify({'success': False, 'message': 'HOD can only give Resubmit option.'})
            if current_status != 'approved':
                 return jsonify({'success': False, 'message': 'HOD can only give Resubmit option after Guide approves the project.'})

        # When status is changed by HOD, clear the resubmission_request flag (so it stops showing as requested)
        if role == 'hod' and status == 'resubmit':
            cursor.execute("UPDATE projects SET status = ?, resubmission_request = NULL, resubmission_reason = NULL WHERE id = ?", (status, project_id))
            
            # Create notifications for Guide and Students
            cursor.execute("""
                SELECT p.title, t.id as team_id, g.user_id as guide_user_id
                FROM projects p 
                JOIN teams t ON p.team_id = t.id 
                LEFT JOIN guides g ON t.guide_id = g.id 
                WHERE p.id = ?
            """, (project_id,))
            team_info = cursor.fetchone()
            if team_info:
                if team_info['guide_user_id']:
                    cursor.execute("INSERT INTO notifications (user_id, sender_id, title, message) VALUES (?, ?, ?, ?)",
                        (team_info['guide_user_id'], session['user_id'], 'Project Resubmission Granted', f'HOD has granted resubmission for project "{team_info["title"]}"'))
                
                cursor.execute("""
                    SELECT s.user_id FROM team_members tm
                    JOIN students s ON tm.student_id = s.id
                    WHERE tm.team_id = ?
                """, (team_info['team_id'],))
                for stu in cursor.fetchall():
                    cursor.execute("INSERT INTO notifications (user_id, sender_id, title, message) VALUES (?, ?, ?, ?)",
                        (stu['user_id'], session['user_id'], 'Project Resubmission Granted', f'HOD has granted resubmission for your project "{team_info["title"]}".'))
        else:
            cursor.execute("UPDATE projects SET status = ? WHERE id = ?", (status, project_id))

        conn.commit()
        return jsonify({'success': True, 'message': 'Status Updated'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def request_resubmission_option():
    role = session.get('role_name')
    if 'user_id' not in session or role not in ['guide', 'student']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.form
    project_id = data.get('project_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if project was actually approved, otherwise no need to ask HOD
        cursor.execute("SELECT status FROM projects WHERE id = ?", (project_id,))
        proj = cursor.fetchone()
        if not proj:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
            
        if proj['status'] != 'approved':
            return jsonify({'success': False, 'message': 'You only need to request a resubmission from the HOD if the project has already been approved.'})
            
        cursor.execute("UPDATE projects SET resubmission_request = ?, resubmission_reason = ? WHERE id = ?", (role, data.get('reason', ''), project_id,))
        
        # Notify HOD
        cursor.execute("""
            SELECT h.user_id, p.title
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            JOIN hods h ON s.department_id = h.department_id
            WHERE p.id = ? LIMIT 1
        """, (project_id,))
        hod_info = cursor.fetchone()
        if hod_info:
            cursor.execute("INSERT INTO notifications (user_id, sender_id, title, message) VALUES (?, ?, ?, ?)",
                (hod_info['user_id'], session['user_id'], 'Resubmission Requested', f'A resubmission request has been submitted for project "{hod_info["title"]}".'))
                
        conn.commit()
        return jsonify({'success': True, 'message': 'Resubmission request has been sent to the HOD.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_notifications():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT n.*, u.username as sender_name, u.email as sender_email
            FROM notifications n
            LEFT JOIN users u ON n.sender_id = u.id
            WHERE n.user_id = ?
            ORDER BY n.created_at DESC
        """, (session['user_id'],))
        notifications = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def mark_notification_read():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    notification_id = request.form.get('notification_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, session['user_id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def evaluate_project():
    if 'user_id' not in session or session.get('role_name') != 'guide':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.form
    project_id = data.get('project_id')
    marks = data.get('marks')
    feedback = data.get('feedback')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM guides WHERE user_id = ?", (session['user_id'],))
        guide = cursor.fetchone()
        
        cursor.execute("SELECT id FROM evaluations WHERE project_id = ?", (project_id,))
        exists = cursor.fetchone()
        
        if exists:
            cursor.execute(
                "UPDATE evaluations SET marks = ?, feedback = ? WHERE project_id = ?",
                (marks, feedback, project_id)
            )
        else:
            cursor.execute(
                "INSERT INTO evaluations (project_id, guide_id, marks, feedback) VALUES (?, ?, ?, ?)",
                (project_id, guide['id'], marks, feedback)
            )
        cursor.execute("SELECT s.user_id, p.title FROM projects p JOIN teams t ON p.team_id = t.id JOIN team_members tm ON t.id = tm.team_id JOIN students s ON tm.student_id = s.id WHERE p.id = ?", (project_id,))
        for stu in cursor.fetchall():
             cursor.execute("INSERT INTO notifications (user_id, sender_id, title, message) VALUES (?, ?, ?, ?)",
                 (stu['user_id'], session['user_id'], 'Project Evaluated', f'Your project "{stu["title"]}" has received marks and feedback.'))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Evaluation saved'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_evaluation():
    project_id = request.args.get('project_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evaluations WHERE project_id = ?", (project_id,))
    eval_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if eval_data:
        return jsonify({'success': True, 'evaluation': dict(eval_data)})
    return jsonify({'success': False, 'message': 'No evaluation done yet'})

def create_hod():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    department_id = data.get('department_id')
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if department already has an HOD
        cursor.execute("SELECT 1 FROM hods WHERE department_id = ?", (department_id,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'This department already has an HOD. Use "Change HOD" instead.'})
            
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400

        cursor.execute("SELECT id FROM roles WHERE name = 'hod'")
        role = cursor.fetchone()
        
        cursor.execute(
            "INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (role['id'], name, email, hashed_pw)
        )
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO hods (user_id, department_id, plain_password) VALUES (?, ?, ?)",
            (user_id, department_id, password)
        )
        
        conn.commit()
        return jsonify({'success': True, 'message': 'HOD created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_department():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    name = data.get('name')
    description = data.get('description')
    
    if not name:
        return jsonify({'success': False, 'message': 'Department name is required'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO departments (name, description) VALUES (?, ?)", (name, description))
        dept_id = cursor.lastrowid
        
        # Default sections B1, B2, B3
        for section in ['B1', 'B2', 'B3']:
            cursor.execute("INSERT INTO sections (name, department_id) VALUES (?, ?)", (section, dept_id))
            
        conn.commit()
        return jsonify({'success': True, 'message': 'Department and default sections B1, B2, B3 created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_admin_stats():
    print("API: get_admin_stats called")
    if 'user_id' not in session or session.get('role_name') != 'admin':
        print(f"Unauthorized access attempt to get_admin_stats. Session: {session}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    stats = {}
    
    try:
        cursor.execute("SELECT COUNT(*) as count FROM users")
        stats['users'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM projects")
        stats['projects'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM departments")
        stats['departments_count'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM hods")
        stats['hods_count'] = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM users u JOIN roles r ON u.role_id = r.id WHERE r.name = 'clerk'")
        stats['clerks_count'] = cursor.fetchone()['count']

        # Get department list with HOD names and passwords
        cursor.execute("""
            SELECT d.id, d.name, d.is_active, u.username as hod_name, u.email as hod_email, h.plain_password as hod_password, u.id as hod_user_id
            FROM departments d
            LEFT JOIN hods h ON d.id = h.department_id
            LEFT JOIN users u ON h.user_id = u.id
        """)
        stats['departments'] = [dict(row) for row in cursor.fetchall()]
        
        print(f"API: returning stats for {stats['users']} users and {len(stats['departments'])} departments")
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        print(f"API ERROR in get_admin_stats: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_all_users():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    dept_name = request.args.get('department')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT u.id, u.username, u.email, r.name as role, u.created_at, u.is_active,
                   COALESCE(d1.name, d2.name, d3.name) as department_name,
                   CASE 
                     WHEN r.name = 'student' THEN s.roll_number
                     ELSE NULL 
                   END as detail,
                   h.plain_password as hod_password,
                   s.plain_password as student_password
            FROM users u
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN students s ON u.id = s.user_id
            LEFT JOIN guides g ON u.id = g.user_id
            LEFT JOIN hods h ON u.id = h.user_id
            LEFT JOIN departments d1 ON s.department_id = d1.id
            LEFT JOIN departments d2 ON g.department_id = d2.id
            LEFT JOIN departments d3 ON h.department_id = d3.id
        """
        params = []
        if dept_name:
            query += " WHERE COALESCE(d1.name, d2.name, d3.name) = ?"
            params.append(dept_name)
            
        query += " ORDER BY u.created_at DESC"
        
        cursor.execute(query, params)
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_admin_logs():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, u.username, r.name as role 
        FROM login_logs l 
        JOIN users u ON l.user_id = u.id 
        JOIN roles r ON u.role_id = r.id 
        ORDER BY l.login_time DESC LIMIT 50
    """)
    logs = [dict(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify({'success': True, 'logs': logs})

def get_hod_teams():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get HOD's department
    cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
    hod = cursor.fetchone()
    
    if hod:
        query = """
            SELECT t.id, t.name, t.is_solo, t.guide_id, t.academic_year, 
                   p.title as project_title, p.status, p.resubmission_request, p.resubmission_reason, p.semester 
            FROM teams t 
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            LEFT JOIN projects p ON p.team_id = t.id
            WHERE s.department_id = ?
        """
        params = [hod['department_id']]
        
        year = request.args.get('year')
        if year:
            query += " AND t.academic_year = ?"
            params.append(year)
        
        semester = request.args.get('semester')
        if semester:
            query += " AND p.semester = ?"
            params.append(semester)
            
        query += " GROUP BY t.id"
        
        cursor.execute(query, params)
        teams = [dict(row) for row in cursor.fetchall()]
        
        # Get all unique academic years for filtering
        cursor.execute("""
            SELECT DISTINCT t.academic_year 
            FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            WHERE s.department_id = ? AND t.academic_year IS NOT NULL
        """, (hod['department_id'],))
        years = [row['academic_year'] for row in cursor.fetchall()]
        
        # Get all unique semesters for filtering
        cursor.execute("""
            SELECT DISTINCT p.semester 
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            WHERE s.department_id = ? AND p.semester IS NOT NULL AND p.semester != ''
        """, (hod['department_id'],))
        semesters = [row['semester'] for row in cursor.fetchall()]

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'teams': teams, 'years': years, 'semesters': semesters})
    
    cursor.close()
    conn.close()
    return jsonify({'success': False, 'message': 'HOD department not found'})

def create_guide():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get HOD department
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        if not hod:
            return jsonify({'success': False, 'message': 'HOD not found'})
            
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400

        cursor.execute("SELECT id FROM roles WHERE name = 'guide'")
        role = cursor.fetchone()
        
        cursor.execute(
            "INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (role['id'], name, email, hashed_pw)
        )
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO guides (user_id, department_id) VALUES (?, ?)",
            (user_id, hod['department_id'])
        )
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Guide created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_guides():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
    hod = cursor.fetchone()
    
    if hod:
        cursor.execute("""
            SELECT g.id, u.username, u.email, u.is_active, u.id as user_id
            FROM guides g 
            JOIN users u ON g.user_id = u.id 
            WHERE g.department_id = ?
        """, (hod['department_id'],))
        guides = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'guides': guides})
        
    cursor.close()
    conn.close()
    print(f"DEBUG: HOD department not found for user_id {session.get('user_id')}")
    return jsonify({'success': False, 'message': 'HOD department not found', 'user_id': session.get('user_id')})

def assign_guide():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    data = request.form
    team_id = data.get('team_id')
    guide_id = data.get('guide_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if project is already approved
        cursor.execute("SELECT status FROM projects WHERE team_id = ?", (team_id,))
        proj = cursor.fetchone()
        if proj and proj['status'] == 'approved':
            return jsonify({'success': False, 'message': 'Cannot change guide after the project has been approved.'})
            
        cursor.execute("UPDATE teams SET guide_id = ? WHERE id = ?", (guide_id, team_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Guide assigned successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_team_details():
    team_id = request.args.get('team_id')
    if not team_id:
        return jsonify({'success': False, 'message': 'Team ID required'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get team info
        cursor.execute("""
            SELECT t.*, u_guide.username as guide_name, u_guide.email as guide_email
            FROM teams t
            LEFT JOIN guides g ON t.guide_id = g.id
            LEFT JOIN users u_guide ON g.user_id = u_guide.id
            WHERE t.id = ?
        """, (team_id,))
        team = cursor.fetchone()
        
        if not team:
            return jsonify({'success': False, 'message': 'Team not found'})
            
        # Get members
        cursor.execute("""
            SELECT s.roll_number, u.username, u.email, tm.is_leader 
            FROM team_members tm 
            JOIN students s ON tm.student_id = s.id 
            JOIN users u ON s.user_id = u.id 
            WHERE tm.team_id = ?
        """, (team_id,))
        members = [dict(row) for row in cursor.fetchall()]
        
        # Get project
        cursor.execute("SELECT * FROM projects WHERE team_id = ?", (team_id,))
        project = cursor.fetchone()
        project_data = dict(project) if project else None
        
        # Get evaluation
        evaluation_data = None
        if project_data:
            cursor.execute("SELECT * FROM evaluations WHERE project_id = ?", (project_data['id'],))
            evaluation = cursor.fetchone()
            evaluation_data = dict(evaluation) if evaluation else None
            
        return jsonify({
            'success': True, 
            'team': dict(team), 
            'members': members,
            'project': project_data,
            'evaluation': evaluation_data
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_guide_teams():
    if 'user_id' not in session or session.get('role_name') != 'guide':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM guides WHERE user_id = ?", (session['user_id'],))
    guide = cursor.fetchone()
    
    if guide:
        cursor.execute("""
            SELECT t.id, t.name, t.is_solo 
            FROM teams t 
            WHERE t.guide_id = ?
        """, (guide['id'],))
        teams_rows = cursor.fetchall()
        teams = [dict(row) for row in teams_rows]
        team_ids = [t['id'] for t in teams]

        if not team_ids:
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'teams': []})

        # Batch fetch members
        placeholders = ','.join(['?'] * len(team_ids))
        cursor.execute(f"""
            SELECT tm.team_id, s.roll_number, u.username, u.email, tm.is_leader 
            FROM team_members tm 
            JOIN students s ON tm.student_id = s.id 
            JOIN users u ON s.user_id = u.id 
            WHERE tm.team_id IN ({placeholders})
        """, team_ids)
        all_members = cursor.fetchall()

        # Batch fetch projects
        cursor.execute(f"""
            SELECT p.id, p.team_id, p.title, p.abstract, p.tech_stack, p.github_link, p.file_path, p.screenshot_path, p.status, p.resubmission_request, p.resubmission_reason, p.semester, p.website_link 
            FROM projects p 
            WHERE p.team_id IN ({placeholders})
        """, team_ids)
        all_projects = cursor.fetchall()
        project_ids = [p['id'] for p in all_projects]

        # Batch fetch evaluations
        eval_map = {}
        if project_ids:
            ep_placeholders = ','.join(['?'] * len(project_ids))
            cursor.execute(f"SELECT project_id, marks, feedback FROM evaluations WHERE project_id IN ({ep_placeholders})", project_ids)
            for ev in cursor.fetchall():
                eval_map[ev['project_id']] = dict(ev)

        # Organize data
        for team in teams:
            team['members'] = [dict(m) for m in all_members if m['team_id'] == team['id']]
            
            proj = next((dict(p) for p in all_projects if p['team_id'] == team['id']), None)
            if proj:
                proj['evaluation'] = eval_map.get(proj['id'])
            team['project'] = proj

        cursor.close()
        conn.close()
        return jsonify({'success': True, 'teams': teams})
    
    cursor.close()
    conn.close()
    return jsonify({'success': False})


def toggle_department_status():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    dept_id = request.form.get('department_id')
    status = request.form.get('status') # '1' for active, '0' for inactive
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE departments SET is_active = ? WHERE id = ?", (status, dept_id))
        conn.commit()
        msg = "Department activated" if status == '1' else "Department deactivated"
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def delete_hod():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    user_id = request.form.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Soft delete: just deactivate the user
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'HOD account deactivated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def toggle_user_status():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    target_user_id = request.form.get('target_user_id')
    new_status = request.form.get('status') # 1 for active, 0 for inactive
    
    if new_status is None:
        # If status not provided, toggle it
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM users WHERE id = ?", (target_user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'})
        new_status = 0 if user['is_active'] == 1 else 1
    else:
        new_status = int(new_status)
        conn = get_db_connection()
        cursor = conn.cursor()

    try:
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, target_user_id))
        conn.commit()
        status_text = "activated" if new_status == 1 else "deactivated"
        return jsonify({'success': True, 'message': f'User {status_text} successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def change_user_email():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    target_user_id = request.form.get('target_user_id', '').strip()
    new_email = request.form.get('new_email', '').strip()

    if not target_user_id:
        return jsonify({'success': False, 'message': 'Target user ID is required'})

    if not new_email or '@' not in new_email:
        return jsonify({'success': False, 'message': 'Invalid email address'})

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check the target user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (target_user_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': 'User not found'})

        # Check if email is already taken by a different user
        cursor.execute("SELECT id FROM users WHERE email = ? AND id != ?", (new_email, target_user_id))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email address is already in use by another account'})

        cursor.execute("UPDATE users SET email = ? WHERE id = ?", (new_email, target_user_id))
        conn.commit()

        # Verify the update was actually applied
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'No rows were updated. Please try again.'})

        return jsonify({
            'success': True,
            'message': 'Email updated successfully',
            'new_email': new_email
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def change_hod():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    dept_id = request.form.get('department_id')
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete old HOD if exists
        cursor.execute("SELECT user_id FROM hods WHERE department_id = ?", (dept_id,))
        old_hod = cursor.fetchone()
        if old_hod:
             # Soft delete: just deactivate the old HOD user
             cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (old_hod['user_id'],))
             # We might need to remove them from the 'hods' table to assign a new one, 
             # but we keep the 'users' record which is the main identity.
             cursor.execute("DELETE FROM hods WHERE user_id = ?", (old_hod['user_id'],))
        
        # Create new HOD
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("SELECT id FROM roles WHERE name = 'hod'")
        role_id = cursor.fetchone()['id']
        cursor.execute("INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)", (role_id, name, email, hashed_pw))
        user_id = cursor.lastrowid
        cursor.execute("INSERT INTO hods (user_id, department_id, plain_password) VALUES (?, ?, ?)", (user_id, dept_id, password))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'HOD changed successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_teaching_staff_for_dept():
    """Admin: get all guides (teaching staff) for a specific department."""
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    dept_id = request.args.get('department_id')
    if not dept_id:
        return jsonify({'success': False, 'message': 'Department ID required'})
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT g.id as guide_id, u.id as user_id, u.username, u.email
            FROM guides g
            JOIN users u ON g.user_id = u.id
            WHERE g.department_id = ?
            ORDER BY u.username
        """, (dept_id,))
        staff = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'staff': staff})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def assign_existing_staff_as_hod():
    """Admin: promote an existing guide user to HOD for a department."""
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    dept_id = request.form.get('department_id')
    guide_user_id = request.form.get('guide_user_id')  # user_id of the selected guide
    if not dept_id or not guide_user_id:
        return jsonify({'success': False, 'message': 'Department ID and staff member are required'})
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Remove old HOD for this department (but keep their user account)
        cursor.execute("SELECT user_id FROM hods WHERE department_id = ?", (dept_id,))
        old_hod = cursor.fetchone()
        if old_hod and str(old_hod['user_id']) != str(guide_user_id):
            # Change the old HOD user back to 'guide' role if they were a guide, else just remove hod record
            cursor.execute("SELECT id FROM roles WHERE name = 'guide'")
            guide_role = cursor.fetchone()
            cursor.execute("SELECT id FROM guides WHERE user_id = ?", (old_hod['user_id'],))
            was_guide = cursor.fetchone()
            if was_guide:
                # Restore to guide role
                cursor.execute("UPDATE users SET role_id = ? WHERE id = ?", (guide_role['id'], old_hod['user_id']))
            else:
                # Soft delete: deactivate the old HOD user account
                cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (old_hod['user_id'],))
            cursor.execute("DELETE FROM hods WHERE department_id = ?", (dept_id,))

        # Get selected guide details
        cursor.execute("SELECT u.username, u.email FROM users u WHERE u.id = ?", (guide_user_id,))
        guide_user = cursor.fetchone()
        if not guide_user:
            return jsonify({'success': False, 'message': 'Selected staff member not found'})

        # Check if the guide is already an HOD somewhere else
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (guide_user_id,))
        existing_hod = cursor.fetchone()
        if existing_hod:
            return jsonify({'success': False, 'message': 'This staff member is already an HOD in another department'})

        # Change the user role to 'hod'
        cursor.execute("SELECT id FROM roles WHERE name = 'hod'")
        hod_role = cursor.fetchone()
        cursor.execute("UPDATE users SET role_id = ? WHERE id = ?", (hod_role['id'], guide_user_id))

        # guides table does not store plain_password; use empty string
        plain_pw = ''

        # Insert into hods table
        cursor.execute(
            "INSERT INTO hods (user_id, department_id, plain_password) VALUES (?, ?, ?)",
            (guide_user_id, dept_id, plain_pw)
        )

        conn.commit()
        return jsonify({'success': True, 'message': f'{guide_user["username"]} has been assigned as HOD successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_admin_watch_details():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    department_name = request.args.get('department')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT d.name as department, u1.username as hod_name, u2.username as guide_name, 
                   t.name as team_name, u3.username as student_name, s.roll_number
            FROM departments d
            LEFT JOIN hods h ON d.id = h.department_id
            LEFT JOIN users u1 ON h.user_id = u1.id
            LEFT JOIN guides g ON d.id = g.department_id
            LEFT JOIN users u2 ON g.user_id = u2.id
            LEFT JOIN teams t ON g.id = t.guide_id
            LEFT JOIN team_members tm ON t.id = tm.team_id
            LEFT JOIN students s ON tm.student_id = s.id
            LEFT JOIN users u3 ON s.user_id = u3.id
        """
        params = []
        if department_name:
            query += " WHERE d.name = ?"
            params.append(department_name)
            
        cursor.execute(query, params)
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_admin_project_report():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get all team projects and their metadata, grouped by department and academic year
        query = """
            SELECT 
                d.name as department_name, 
                t.academic_year, 
                t.name as team_name, 
                p.title as project_title, 
                p.status, 
                p.semester,
                p.screenshot_path,
                u_guide.username as guide_name,
                GROUP_CONCAT(u_stu.username, ', ') as members
            FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            JOIN users u_stu ON s.user_id = u_stu.id
            JOIN departments d ON s.department_id = d.id
            LEFT JOIN projects p ON p.team_id = t.id
            LEFT JOIN guides g ON t.guide_id = g.id
            LEFT JOIN users u_guide ON g.user_id = u_guide.id
            GROUP BY t.id
            ORDER BY d.name ASC, t.academic_year DESC, t.name ASC
        """
        cursor.execute(query)
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        print(f"ERROR in get_admin_project_report: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_hod_project_report():
    """HOD: project report scoped to their own department only."""
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        if not hod:
            return jsonify({'success': False, 'message': 'HOD record not found'})
        dept_id = hod['department_id']
        cursor.execute("""
            SELECT 
                d.name as department_name,
                t.academic_year,
                t.name as team_name,
                p.title as project_title,
                p.status,
                p.semester,
                u_guide.username as guide_name,
                GROUP_CONCAT(u_stu.username, ', ') as members
            FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            JOIN users u_stu ON s.user_id = u_stu.id
            JOIN departments d ON s.department_id = d.id
            LEFT JOIN projects p ON p.team_id = t.id
            LEFT JOIN guides g ON t.guide_id = g.id
            LEFT JOIN users u_guide ON g.user_id = u_guide.id
            WHERE s.department_id = ?
            GROUP BY t.id
            ORDER BY t.academic_year DESC, t.name ASC
        """, (dept_id,))
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_guide_project_report():
    """Guide: project report scoped to only their assigned teams."""
    if 'user_id' not in session or session.get('role_name') != 'guide':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM guides WHERE user_id = ?", (session['user_id'],))
        guide = cursor.fetchone()
        if not guide:
            return jsonify({'success': False, 'message': 'Guide record not found'})
        cursor.execute("""
            SELECT 
                d.name as department_name,
                t.academic_year,
                t.name as team_name,
                p.title as project_title,
                p.status,
                p.semester,
                p.abstract,
                p.tech_stack,
                e.marks,
                e.feedback,
                GROUP_CONCAT(u_stu.username, ', ') as members
            FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            JOIN users u_stu ON s.user_id = u_stu.id
            JOIN departments d ON s.department_id = d.id
            LEFT JOIN projects p ON p.team_id = t.id
            LEFT JOIN evaluations e ON e.project_id = p.id
            WHERE t.guide_id = ?
            GROUP BY t.id
            ORDER BY t.academic_year DESC, t.name ASC
        """, (guide['id'],))
        data = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_clerk_stats():
    if 'user_id' not in session or session.get('role_name') != 'clerk':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Total departments
        cursor.execute("SELECT COUNT(*) as count FROM departments")
        depts_count = cursor.fetchone()['count']
        
        # Total students
        cursor.execute("SELECT COUNT(*) as count FROM students")
        students_count = cursor.fetchone()['count']
        
        # Departments list with student counts
        cursor.execute("""
            SELECT d.id, d.name, COUNT(s.id) as student_count
            FROM departments d
            LEFT JOIN students s ON d.id = s.department_id
            GROUP BY d.id
        """)
        departments = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True, 
            'stats': {
                'departments': depts_count,
                'students': students_count
            },
            'departments': departments
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_student_by_clerk():
    if 'user_id' not in session or session.get('role_name') != 'clerk':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    name = data.get('name')
    email = data.get('email')
    roll = data.get('roll')
    dept_id = data.get('department_id')
    password = data.get('password')
    academic_year = data.get('academic_year')
    
    if not all([name, email, roll, dept_id, password, academic_year]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if email/roll already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400
            
        cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Roll number already registered.'}), 400

        # Get role ID for student
        cursor.execute("SELECT id FROM roles WHERE name = 'student'")
        role = cursor.fetchone()
        
        # Insert user
        cursor.execute(
            "INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (role['id'], name, email, hashed_pw)
        )
        user_id = cursor.lastrowid
        
        # Insert student record
        cursor.execute(
            "INSERT INTO students (user_id, roll_number, department_id, plain_password, academic_year) VALUES (?, ?, ?, ?, ?)",
            (user_id, roll, dept_id, password, academic_year)
        )
        
        conn.commit()
        return jsonify({'success': True, 'message': f'Student account for {name} created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_clerk_by_admin():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400

        cursor.execute("SELECT id FROM roles WHERE name = 'clerk'")
        role = cursor.fetchone()
        cursor.execute("INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)",
                       (role['id'], name, email, hashed_pw))
        conn.commit()
        return jsonify({'success': True, 'message': f'Clerk account for {name} created successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_clerks():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT u.id, u.username, u.email, u.created_at
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE r.name = 'clerk'
        """)
        clerks = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'data': clerks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()



def get_hod_students():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        if not hod: return jsonify({'success': False, 'message': 'HOD not found'})
        
        section_id = request.args.get('section_id')
        guide_id = request.args.get('guide_id') # From guides table
        
        query = """
            SELECT s.id, u.username, u.email, s.roll_number, t.name as team_name, t.id as team_id,
                   sec.name as section_name, s.section_id, g_u.username as guide_name, t.guide_id,
                   u.is_active, u.id as user_id
            FROM students s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN team_members tm ON s.id = tm.student_id
            LEFT JOIN teams t ON tm.team_id = t.id
            LEFT JOIN sections sec ON s.section_id = sec.id
            LEFT JOIN guides g ON t.guide_id = g.id
            LEFT JOIN users g_u ON g.user_id = g_u.id
            WHERE s.department_id = ?
        """
        params = [hod['department_id']]
        
        if section_id:
            query += " AND s.section_id = ?"
            params.append(section_id)
        if guide_id:
            query += " AND t.guide_id = ?"
            params.append(guide_id)
            
        cursor.execute(query, params)
        students = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'students': students})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def delete_guide():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    guide_id = request.form.get('guide_id') # This is the id from 'guides' table
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM guides WHERE id = ?", (guide_id,))
        user = cursor.fetchone()
        if user:
            # Soft delete: deactivate the user and unassign from teams
            # Do not unassign from teams where project is already approved
            cursor.execute("""
                UPDATE teams SET guide_id = NULL 
                WHERE guide_id = ? 
                AND id NOT IN (SELECT team_id FROM projects WHERE status = 'approved')
            """, (guide_id,))
            cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user['user_id'],))
            conn.commit()
            return jsonify({'success': True, 'message': 'Guide account deactivated'})
        return jsonify({'success': False, 'message': 'Guide not found'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def delete_student():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    student_id = request.form.get('student_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM students WHERE id = ?", (student_id,))
        user = cursor.fetchone()
        if user:
            # Soft delete: deactivate the user
            cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user['user_id'],))
            conn.commit()
            return jsonify({'success': True, 'message': 'Student account deactivated'})
        return jsonify({'success': False, 'message': 'Student not found'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def delete_team():
    if 'user_id' not in session or (session.get('role_name') != 'hod' and session.get('role_name') != 'admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    team_id = request.form.get('team_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM team_members WHERE team_id = ?", (team_id,))
        cursor.execute("DELETE FROM projects WHERE team_id = ?", (team_id,))
        cursor.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Team deleted'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_student_by_hod():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    name = data.get('name')
    email = data.get('email')
    roll = data.get('roll')
    password = data.get('password')
    academic_year = data.get('academic_year')
    
    if not all([name, email, roll, password, academic_year]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Get HOD's department
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        if not hod:
            return jsonify({'success': False, 'message': 'HOD department not found.'}), 404
        
        dept_id = hod['department_id']
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Check if email/roll already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400
            
        cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Roll number already registered.'}), 400
            
        # Insert user
        cursor.execute("SELECT id FROM roles WHERE name = 'student'")
        role = cursor.fetchone()
        cursor.execute("INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)", 
                       (role['id'], name, email, hashed_pw))
        user_id = cursor.lastrowid
        
        # Insert student record
        cursor.execute("INSERT INTO students (user_id, roll_number, department_id, plain_password, academic_year) VALUES (?, ?, ?, ?, ?)", 
                       (user_id, roll, dept_id, password, academic_year))
        conn.commit()
        return jsonify({'success': True, 'message': 'Student created successfully!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_student_by_admin():
    if 'user_id' not in session or session.get('role_name') != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    data = request.form
    name = data.get('name')
    email = data.get('email')
    roll = data.get('roll')
    password = data.get('password')
    academic_year = data.get('academic_year')
    dept_id = data.get('department_id')
    
    if not all([name, email, roll, password, academic_year, dept_id]):
        return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Check if email/roll already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email already registered.'}), 400
            
        cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Roll number already registered.'}), 400
            
        # Insert user
        cursor.execute("SELECT id FROM roles WHERE name = 'student'")
        role = cursor.fetchone()
        cursor.execute("INSERT INTO users (role_id, username, email, password_hash) VALUES (?, ?, ?, ?)", 
                       (role['id'], name, email, hashed_pw))
        user_id = cursor.lastrowid
        
        # Insert student record
        cursor.execute("INSERT INTO students (user_id, roll_number, department_id, plain_password, academic_year) VALUES (?, ?, ?, ?, ?)", 
                       (user_id, roll, dept_id, password, academic_year))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Student created successfully by Admin!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_hod_stats():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as count FROM guides WHERE department_id = ?", (hod['department_id'],))
        staff_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM students WHERE department_id = ?", (hod['department_id'],))
        student_count = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(t.id) as count 
            FROM teams t 
            JOIN team_members tm ON t.id = tm.team_id
            JOIN students s ON tm.student_id = s.id
            WHERE s.department_id = ?
            GROUP BY t.id
        """, (hod['department_id'],))
        teams_count = len(cursor.fetchall())
        
        return jsonify({
            'success': True,
            'stats': {
                'staff': staff_count,
                'students': student_count,
                'teams': teams_count
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_sections():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        
        cursor.execute("""
            SELECT s.*, u.username as coordinator_name 
            FROM sections s 
            LEFT JOIN guides g ON s.coordinator_id = g.id
            LEFT JOIN users u ON g.user_id = u.id
            WHERE s.department_id = ?
        """, (hod['department_id'],))
        sections = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'sections': sections})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def create_section():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    name = request.form.get('name')
    coordinator_id = request.form.get('coordinator_id') # nullable
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT department_id FROM hods WHERE user_id = ?", (session['user_id'],))
        hod = cursor.fetchone()
        
        cursor.execute("INSERT INTO sections (name, department_id, coordinator_id) VALUES (?, ?, ?)", 
                       (name, hod['department_id'], coordinator_id if coordinator_id else None))
        conn.commit()
        return jsonify({'success': True, 'message': 'Section created'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def assign_guide_to_section():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    section_id = request.form.get('section_id')
    guide_id = request.form.get('guide_id') # From guides table
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update section coordinator
        cursor.execute("UPDATE sections SET coordinator_id = ? WHERE id = ?", (guide_id if guide_id else None, section_id))
        
        # Auto-assign this guide to all teams belonging to this section
        if guide_id:
            cursor.execute("""
                UPDATE teams SET guide_id = ? 
                WHERE id IN (
                    SELECT tm.team_id 
                    FROM team_members tm
                    JOIN students s ON tm.student_id = s.id
                    WHERE s.section_id = ?
                )
                AND id NOT IN (SELECT team_id FROM projects WHERE status = 'approved')
            """, (guide_id, section_id))
            
        conn.commit()
        return jsonify({'success': True, 'message': 'Guide assigned to section and all related teams updated'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def assign_section():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
    student_id = request.form.get('student_id')
    section_id = request.form.get('section_id') # can be '' for unassign
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE students SET section_id = ? WHERE id = ?", (section_id if section_id else None, student_id))
        
        # Auto-assign guide if section has a coordinator
        if section_id:
            cursor.execute("SELECT coordinator_id FROM sections WHERE id = ?", (section_id,))
            sec = cursor.fetchone()
            if sec and sec['coordinator_id']:
                # Find student's team
                cursor.execute("SELECT team_id FROM team_members WHERE student_id = ?", (student_id,))
                tm = cursor.fetchone()
                if tm:
                    # Check if project is already approved before auto-assigning from section coordinator
                    cursor.execute("SELECT status FROM projects WHERE team_id = ?", (tm['team_id'],))
                    proj = cursor.fetchone()
                    if not proj or proj['status'] != 'approved':
                        cursor.execute("UPDATE teams SET guide_id = ? WHERE id = ?", (sec['coordinator_id'], tm['team_id']))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Section assigned'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def assign_guide_to_student_team():
    if 'user_id' not in session or session.get('role_name') != 'hod':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    student_id = request.form.get('student_id')
    guide_id = request.form.get('guide_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT team_id FROM team_members WHERE student_id = ?", (student_id,))
        tm = cursor.fetchone()
        if not tm:
            return jsonify({'success': False, 'message': 'Student has no team'})
            
        # Handle unassign or specific guide
        actual_guide = guide_id if (guide_id and guide_id != '') else None
        
        # Check if project is already approved
        cursor.execute("SELECT status FROM projects WHERE team_id = ?", (tm['team_id'],))
        proj = cursor.fetchone()
        if proj and proj['status'] == 'approved':
            return jsonify({'success': False, 'message': 'Cannot change guide after the project has been approved.'})

        cursor.execute("UPDATE teams SET guide_id = ? WHERE id = ?", (actual_guide, tm['team_id']))
        conn.commit()
        return jsonify({'success': True, 'message': 'Guide assigned successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def get_user_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    role = session['role_name']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Basic user info
        cursor.execute("SELECT u.id, u.username, u.email, u.profile_photo, u.created_at, r.name as role FROM users u JOIN roles r ON u.role_id = r.id WHERE u.id = ?", (user_id,))
        user = dict(cursor.fetchone())
        
        detail_info = {}
        if role == 'student':
            cursor.execute("""
                SELECT s.roll_number, d.name as department_name, t.name as team_name, u_guide.username as guide_name
                FROM students s
                LEFT JOIN departments d ON s.department_id = d.id
                LEFT JOIN team_members tm ON s.id = tm.student_id
                LEFT JOIN teams t ON tm.team_id = t.id
                LEFT JOIN guides g ON t.guide_id = g.id
                LEFT JOIN users u_guide ON g.user_id = u_guide.id
                WHERE s.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            detail_info = dict(row) if row else {}
        elif role == 'guide':
            cursor.execute("""
                SELECT d.name as department_name, (SELECT COUNT(*) FROM teams WHERE guide_id = g.id) as team_count
                FROM guides g
                JOIN departments d ON g.department_id = d.id
                WHERE g.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            detail_info = dict(row) if row else {}
        elif role == 'hod':
            cursor.execute("""
                SELECT d.name as department_name, d.description as department_description
                FROM hods h
                JOIN departments d ON h.department_id = d.id
                WHERE h.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            detail_info = dict(row) if row else {}
            
        user['details'] = detail_info
        return jsonify({'success': True, 'profile': user})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

def upload_profile_photo():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    
    if file:
        filename = str(int(time.time())) + "_" + secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_PROFILE_FOLDER'], filename))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Store ONLY the filename in the DB, the route handles the directory part
            cursor.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (filename, session['user_id']))
            conn.commit()
            return jsonify({'success': True, 'photo_url': filename})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
        finally:
            cursor.close()
            conn.close()
    return jsonify({'success': False, 'message': 'Internal Error'}), 500

@app.route('/')
def serve_index():
    return send_from_directory('../', 'index.html')

@app.route('/frontend/<path:path>')
def serve_frontend(path):
    return send_from_directory('../frontend', path)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/profile_photos/<path:filename>')
def serve_profile_photo(filename):
    return send_from_directory(app.config['UPLOAD_PROFILE_FOLDER'], filename)

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    # Access control: 
    # 1. Logged in users (admin, guide, hod, clerk, student) can view screenshots
    # 2. Public users can ONLY view screenshots of 'approved' projects (for the gallery)
    if 'user_id' not in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM projects WHERE screenshot_path = ?", (filename,))
        proj = cursor.fetchone()
        cursor.close()
        conn.close()
        if not proj or proj['status'] != 'approved':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
            
    return send_from_directory(app.config['UPLOAD_SCREENSHOT_FOLDER'], filename)

def get_project_by_id():
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({'success': False, 'message': 'Project ID required'}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get project details along with guide and department
        query = """
            SELECT 
                p.*, 
                d.name as department_name, 
                ug.username as guide_name,
                ug.email as guide_email,
                t.name as team_name
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            JOIN guides g ON t.guide_id = g.id
            JOIN users ug ON g.user_id = ug.id
            JOIN departments d ON g.department_id = d.id
            WHERE p.id = ?
        """
        cursor.execute(query, (project_id,))
        project = cursor.fetchone()
        
        if not project:
            return jsonify({'success': False, 'message': 'Project not found'}), 404
            
        # Get team members
        cursor.execute("""
            SELECT u.username, tm.is_leader 
            FROM team_members tm 
            JOIN students s ON tm.student_id = s.id 
            JOIN users u ON s.user_id = u.id 
            WHERE tm.team_id = ?
            ORDER BY tm.is_leader DESC
        """, (project['team_id'],))
        members = [dict(row) for row in cursor.fetchall()]
        
        # Get all screenshots
        cursor.execute("SELECT screenshot_path FROM project_screenshots WHERE project_id = ?", (project['id'],))
        screenshots = [row['screenshot_path'] for row in cursor.fetchall()]
        
        project_dict = dict(project)
        project_dict['members'] = members
        project_dict['screenshots'] = screenshots
        
        return jsonify({'success': True, 'project': project_dict})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

def get_approved_projects():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT 
                p.id,
                p.title, 
                p.abstract as description, 
                d.name as department, 
                u.username as guided_by, 
                p.github_link,
                t.academic_year,
                p.screenshot_path,
                p.website_link
            FROM projects p
            JOIN teams t ON p.team_id = t.id
            JOIN guides g ON t.guide_id = g.id
            JOIN users u ON g.user_id = u.id
            JOIN departments d ON g.department_id = d.id
            WHERE p.status = 'approved'
            ORDER BY p.submitted_at DESC
        """
        cursor.execute(query)
        projects = []
        for row in cursor.fetchall():
            p = dict(row)
            # Fetch all screenshots for this project
            cursor.execute("SELECT screenshot_path FROM project_screenshots WHERE project_id = ?", (p['id'],))
            p['screenshots'] = [r['screenshot_path'] for r in cursor.fetchall()]
            projects.append(p)
        
        # Get all distinct active departments
        cursor.execute("SELECT name FROM departments WHERE is_active = 1 ORDER BY name")
        all_departments = [row['name'] for row in cursor.fetchall()]
        
        # Get all distinct academic years
        cursor.execute("SELECT DISTINCT academic_year FROM teams WHERE academic_year IS NOT NULL AND academic_year != '' ORDER BY academic_year DESC")
        all_years = [row['academic_year'] for row in cursor.fetchall()]
        
        return jsonify({
            'success': True, 
            'projects': projects, 
            'departments': all_departments, 
            'years': all_years
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
