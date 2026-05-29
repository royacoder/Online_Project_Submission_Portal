import mysql.connector
import bcrypt

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'online_project_submission'
}

password = "admin123"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def reset_admin():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Update admin user
        cursor.execute("UPDATE users SET password_hash = %s WHERE email = 'admin@portal.com'", (hashed,))
        conn.commit()
        
        print(f"Admin password reset to 'admin123' with valid Python bcrypt hash.")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to reset admin: {e}")

if __name__ == "__main__":
    reset_admin()
