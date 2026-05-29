import mysql.connector
import os

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root', 
}

db_name = 'online_project_submission'
schema_path = os.path.join(os.path.dirname(__file__), '../database/schema.sql')

def setup_database():
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Create database
        print(f"Creating database {db_name} if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        
        # Read and execute schema.sql
        print(f"Reading schema from {schema_path}...")
        with open(schema_path, 'r', encoding='utf-8') as f:
            sql_commands = f.read().split(';')
            
        print("Executing schema commands...")
        for command in sql_commands:
            if command.strip():
                try:
                    cursor.execute(command)
                except Exception as e:
                    print(f"Error executing command: {command[:50]}...\n{e}")
        
        conn.commit()
        print("Database setup complete!")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to setup database: {e}")

if __name__ == "__main__":
    setup_database()
