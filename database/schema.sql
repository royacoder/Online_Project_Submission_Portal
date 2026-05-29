-- Database: online_project_submission
CREATE DATABASE IF NOT EXISTS online_project_submission;
USE online_project_submission;

-- 1. Roles
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);

-- Insert Default Roles
INSERT INTO roles (name) VALUES ('admin'), ('hod'), ('guide'), ('student');

-- 2. Users (Base table for authentication)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_id INT NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);

-- 3. Departments
CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT
);

-- 4. HODs
CREATE TABLE hods (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    department_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- 5. Guides
CREATE TABLE guides (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    department_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- 6. Students
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    roll_number VARCHAR(50) NOT NULL UNIQUE,
    department_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

-- 7. Teams (Solo or 2-person team)
CREATE TABLE teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    guide_id INT NULL, -- Assigned by HOD later
    is_solo BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guide_id) REFERENCES guides(id) ON DELETE SET NULL
);

-- 8. Team Members
CREATE TABLE team_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    student_id INT NOT NULL,
    is_leader BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE (student_id) -- A student can belong to only one team
);

-- 9. Projects
CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    abstract TEXT NOT NULL,
    tech_stack VARCHAR(255) NOT NULL,
    github_link VARCHAR(255),
    file_path VARCHAR(255), -- Uploaded ZIP/PDF path
    status ENUM('pending', 'approved', 'rejected', 'resubmit') DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);

-- 10. Evaluations
CREATE TABLE evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL UNIQUE,
    guide_id INT NOT NULL,
    marks DECIMAL(5, 2),
    feedback TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (guide_id) REFERENCES guides(id) ON DELETE CASCADE
);

-- 11. Login Logs
CREATE TABLE login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL DEFAULT NULL,
    session_duration INT NULL COMMENT 'Duration in seconds',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Sample Data --
-- Insert Admin User (Password: admin123 -> Hash it in PHP, here using plain 'admin123' hashed with BCRYPT for demo purposes but can use dummy hashes initially)
-- Wait, using PHP's password_hash('admin123', PASSWORD_BCRYPT) gives something like $2y$10$...
-- I'll insert a pre-hashed password for admin: 'admin123'
INSERT INTO users (role_id, username, email, password_hash)
VALUES (1, 'Admin User', 'admin@portal.com', '$2y$10$eOPEo8Zq2sE5q1.0nO.7HOS7b7eO8/9U1wN4S590fO9aJ0W3xNyeG');

INSERT INTO departments (name, description) VALUES ('Computer Science', 'CS Department'), ('Information Technology', 'IT Department');

-- We'll register HOD, Guide, and Students through the application, or you can register them from the admin panel!
