# PROJECT REPORT: ONLINE PROJECT SUBMISSION PORTAL

## 1. INTRODUCTION

### Purpose of the Project
The **Online Project Submission Portal** is designed to digitize and streamline the management of academic projects within educational institutions. Its primary purpose is to provide a centralized platform where students can collaborate, submit deliverables, and receive feedback, while faculty and administration can efficiently monitor and evaluate progress.

### Problem Statement
Traditionally, academic project management involves manual paperwork, fragmented communication via emails or physical storage, and lack of a structured tracking system. Key issues include:
*   Difficulty in monitoring team formation and guide assignment.
*   Risk of losing project deliverables (documents, source code).
*   Lack of transparency in the evaluation process.
*   Absence of a public showcase for high-quality student work.

### Objectives and Goals
*   **Centralization:** Create a single source of truth for all project-related data.
*   **Automation:** Streamline the workflow from team formation to final evaluation.
*   **Accountability:** Implement role-based access control (RBAC) to ensure distinct responsibilities for Students, Guides, HODs, and Admins.
*   **Visibility:** Provide a public gallery for approved projects to inspire future students and industry partners.

---

## 2. EXISTING SYSTEM

### Current System Description
In many academic settings, project management is still handled through manual or semi-automated processes. Students submit projects via physical media (CDs/Pendrives) or email attachments to individual guides. Guides maintain manual registers or spreadsheets to track marks and attendance.

### Drawbacks and Limitations
*   **Data Fragmentation:** Information is scattered across various email threads and physical storage devices.
*   **Communication Lag:** Students often face significant delays in receiving feedback on their submissions.
*   **Inconsistency:** There is no standardized format for submissions, leading to confusion during evaluation.
*   **Difficulty in Tracking History:** It is hard to maintain a history of resubmissions and changes requested by guides.
*   **Poor Accessibility:** Exceptional projects remain hidden in archives and are not accessible to the public or junior students for learning.

---

## 3. PROPOSED SYSTEM / FUNCTIONALITY

### New System Description
The proposed system is a comprehensive web-based portal that automates the entire academic project lifecycle. It features a responsive UI and a robust backend to handle multi-role interactions, secure file uploads, and real-time administrative oversight.

### Features and Advantages
*   **Multi-Role Dashboards:** Tailored interfaces for Students, Guides, HODs, Clerks, and Admins.
*   **Team Management:** Support for both solo and group teams with automated membership tracking.
*   **Deliverable Tracking:** Secure submission of source code (ZIP), documentation (PDF), and visual previews (Screenshots).
*   **Integrated Evaluation:** Guides can provide marks and qualitative feedback directly through the portal.
*   **Public Project Gallery:** A searchable interface showcasing approved projects to the public without login.
*   **Reporting System:** One-click CSV/Excel report generation for department-wide performance tracking.
*   **Security:** Industry-standard password hashing (Bcrypt) and session-based authentication.

---

## 4. TOOLS, PROGRAMMING LANGUAGES, AND DATABASE USED

### Technology Stack
*   **Frontend:**
    *   **HTML5 & CSS3:** For semantic structure and custom, high-performance styling.
    *   **JavaScript (ES6+):** For dynamic UI updates and asynchronous communication with the backend.
    *   **Bootstrap 5:** Used for its responsive grid system and pre-built UI components.
*   **Backend:**
    *   **Python (Flask):** A lightweight yet powerful framework chosen for its efficiency in building RESTful APIs.
    *   **Bcrypt:** For secure, salt-based password hashing.
    *   **Flask-Session:** For managing user authentication states across requests.
*   **Database:**
    *   **SQLite / MySQL:** For structured data storage. SQLite is used for its portable, file-based nature, making it ideal for institutional deployment.

### Rationale for Selection
Python was selected for its readability and vast ecosystem of libraries. The choice of a SQL database ensures data integrity and supports complex relationships between users, teams, and projects.

---

## 5. SYSTEM DESIGN

### ER Diagram Description
The system follows a relational data model with the following key entities:
*   **Users:** The core entity for authentication, linked to specific roles.
*   **Students:** Extends the User entity with academic details like Roll Number and Department.
*   **Guides:** Extends the User entity, associated with specific departments for project supervision.
*   **Teams:** Groups of students assigned to a specific guide for a project.
*   **Projects:** The central entity storing titles, abstracts, and file links.
*   **Evaluations:** Linked to projects to store marks and feedback provided by guides.

### Data Flow Diagram (DFD)
*   **Level 0 (Context):** Users (Student/Guide/Admin) interact with the Portal to submit or retrieve project information.
*   **Level 1:**
    *   **Process 1.0 (Auth):** Verifies user credentials.
    *   **Process 2.0 (Submission):** Handles the upload and storage of project deliverables.
    *   **Process 3.0 (Evaluation):** Allows guides to review and mark submitted work.
    *   **Process 4.0 (Public View):** Fetches and displays approved projects for guest users.

---

## 6. DATA DICTIONARY

### Table: users
| Field | Type | Description |
| :--- | :--- | :--- |
| id | INTEGER | Primary Key |
| role_id | INTEGER | Foreign Key (roles.id) |
| username | TEXT | Full name of the user |
| email | TEXT | Unique login identifier |
| password_hash| TEXT | Secure hashed password |

### Table: projects
| Field | Type | Description |
| :--- | :--- | :--- |
| id | INTEGER | Primary Key |
| team_id | INTEGER | Foreign Key (teams.id) |
| title | TEXT | Title of the project |
| abstract | TEXT | Detailed summary of the work |
| status | TEXT | current state (pending, approved, etc.) |

---

## 7. SCREENS AND DESIGN ELEMENTS

### UI/UX Design philosophy
The application utilizes a **Modern Glassmorphism** design language. It focuses on clarity, ease of navigation, and visual hierarchy using a consistent color palette (Primary: Indigo, Secondary: Amber).

### Screen Descriptions
*   **Authentication Screen:** A secure login portal with password toggle and forgot password functionality.
*   **Student Dashboard:** A central hub showing team details, guide information, and a progress tracker for submissions.
*   **Project Submission Form:** A comprehensive form including file selectors for ZIP/PDF and a multiple-image uploader for screenshots.
*   **Guide Review Panel:** A specialized view for faculty to browse assigned projects, view screenshots in a lightbox, and submit grades.
*   **Admin Control Center:** A high-level dashboard with statistics, department management, and user activation toggles.

---

## 8. LIMITATIONS
*   **File Size Constraints:** Large project files may hit server-side upload limits if not configured otherwise.
*   **Manual Activation:** New users (HODs/Clerks) currently require manual creation or activation by the Super Admin.
*   **Static Previews:** Only image-based previews are available; there is no live code execution environment within the portal.

---

## 9. CONCLUSION
The Online Project Submission Portal provides a robust solution to the long-standing problem of unorganized academic project management. By centralizing the workflow, it ensures transparency, improves communication, and creates a valuable archive of student achievements.

---

## 10. FUTURE SCOPE
*   **Plagiarism Checker:** Integration with tools like Turnitin or MOSS for original code verification.
*   **Calendar Integration:** Automated deadline reminders and meeting scheduling for guides and teams.
*   **AI Chatbot:** A support bot to help students with common questions regarding submission formats.
*   **Live Demo Integration:** Support for embedding live web demos directly on the project view page.

---

## 11. REFERENCES
*   Flask Documentation: https://flask.palletsprojects.com/
*   Bootstrap UI Library: https://getbootstrap.com/
*   SQLite Documentation: https://www.sqlite.org/
*   Icons by FontAwesome: https://fontawesome.com/
