Informatics Engineering College Educational Platform
An AI-powered educational platform designed specifically for students of the Informatics Engineering College.

🛠️ Technologies Used
Backend: Django 5 + Django REST Framework

Database: PostgreSQL + pgvector

AI: OpenAI GPT-4

Auth: JWT (djangorestframework-simplejwt)

Frontend: HTML Templates + Tailwind CSS (RTL Arabic)

Tasks: Celery + Redis

⚙️ Development Environment Setup
Create Virtual Environment & Install Requirements:

Bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
Configure Environment Variables:

Bash
copy .env.example .env       # Edit values in the .env file
Run Database Services (PostgreSQL + Redis):

Option A (Recommended): Docker

Bash
docker compose up -d
Option B (Windows without Docker):

PowerShell
.\scripts\setup_postgresql_windows.ps1
(Then set USE_SQLITE=false in .env to use PostgreSQL).

Database Migration & Seeding:

Bash
python manage.py migrate
python manage.py setup_database      # Enable pgvector, pg_trgm, unaccent
python manage.py check_database      # Check connection and extensions
python manage.py seed_curriculum     # Seed academic years and courses
python manage.py createsuperuser
Run the Development Server:

Bash
python manage.py runserver
Open your browser at: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

📂 Project Structure
Plaintext
informatics_platform/
├── config/           # Django settings & configurations
├── apps/             # Application modules
│   ├── accounts/     # Authentication & users
│   ├── curriculum/   # Academic years & courses
│   ├── lectures/     # Lectures management
│   ├── ai_services/  # AI integration services
│   ├── guest/        # Guest mode handling
│   ├── progress/     # Student progress tracking
│   └── notifications/# System notifications
├── templates/        # HTML templates
├── static/           # Static files (CSS, JS, Images)
└── media/            # User-uploaded files
📈 Development Phases
Step 1: Project Initialization & Setup

Step 2: Database Configuration

Step 3: Authentication System

Step 5: Layouts, UI & Templates

Step 6: AI Integration

Step 7: Guest Mode Implementation

Step 8: Advanced Features

Step 9: UI/UX Optimization

Step 10: Testing & Deployment
