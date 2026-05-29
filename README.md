# Online Project Submission Portal (Python Backend)

This is a complete web application for managing student project submissions, team formations, and evaluations, now powered by **Python (Flask)** and **MySQL**.

## Role Hierarchy & Scope

The system features robust role-based access control with 4 primary roles: Admin, HOD, Guide, and Student.

## Technology Stack

*   **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.3
*   **Backend**: Python 3 (Flask Framework)
*   **Database**: MySQL
*   **Server**: Flask (Development Server)

## Key Features

*   **RESTful API**: Python Flask implementation of the backend logic.
*   **Database Design**: Structured MySQL database.
*   **Authentication**: Session-based auth with `bcrypt` password hashing.
*   **File Management**: Secure file uploads for project deliverables.

## Setup Instructions

### 1. Database Setup
1. Ensure a MySQL server is running (e.g., via XAMPP or standalone MySQL).
2. Create a database named `online_project_submission`.
3. Import the `database/schema.sql` file into your MySQL server.

### 2. Backend Setup (Python)
1. Navigate to the `python_backend` directory.
2. The project uses a virtual environment:
   ```powershell
   cd python_backend
   .\venv\Scripts\activate
   ```
3. (Optional) Install dependencies if not already present:
   ```powershell
   pip install flask flask-cors mysql-connector-python bcrypt flask-session
   ```
4. Start the backend server:
   ```powershell
   python app.py
   ```
   The server will run at `http://localhost:5000`.

### 3. Frontend Usage
Since the backend is now running on port 5000, you can open the frontend HTML files directly in a browser or serve them with any static web server. 
*   Ensure the `API_URL` in `frontend/js/script.js` matches your local Flask server address.

### Default Credentials:
*   **Admin Email:** `admin@portal.com`
*   **Password:** `admin123`

## Workflows:
1. **Login as Admin** to create Departments and HODs.
2. **Students** can register and create solo or group teams.
3. **Guides** can review projects and provide evaluations.

