# EduLearn - Online Learning & Course Platform

EduLearn is a full-stack educational platform built with Python, Django, SQLite, and Razorpay. It provides an end-to-end learning management system for students, instructors, and administrators.

---

## Features Overview

- **Student Portal**:
  - Course catalog browsing, category filtering, search, and detailed syllabus previews.
  - Shopping cart and checkout with Razorpay payment gateway integration (UPI, cards, net banking).
  - Instant automated payment confirmation and course enrollment emails.
  - Dedicated student dashboard with enrolled courses, progress tracking, and sent instructor inquiries.
  - Student profile management with avatar upload and account synchronization.

- **Instructor Portal**:
  - Course creation, editing, and syllabus management.
  - Lesson uploading with support for videos, external URLs, and secure course notes documents (PDF, DOCX, TXT, PPTX).
  - Direct student inquiry inbox with read receipts and reply management.
  - Public faculty profiles showcasing instructor bio, specialization, and taught courses.

- **Administration Portal**:
  - Independent custom admin portal (`/admin-dashboard/`) with real-time KPI metrics.
  - Student and instructor account management with one-click activation/deactivation.
  - Course moderation and publication status controls.
  - Enrollment tracking and payment transaction reconciliation.

- **Platform Security & Infrastructure**:
  - 6-digit email OTP password recovery.
  - File upload validator with magic bytes inspection and 50 MB limits.
  - Session-level middleware checking for deactivated users.
  - Responsive modern dark/light UI design system built with CSS3 and Bootstrap Icons.

---

## Technology Stack

- **Framework**: Django 6.1 (Python 3.14)
- **Database**: SQLite3 (`db.sqlite3`)
- **Payments**: Razorpay Python SDK (`razorpay>=1.4.1`)
- **Image Processing**: Pillow (`pillow>=11.0.0`)
- **Email Backend**: SMTP (Gmail) with fallback to Console backend in development
- **Environment**: `python-dotenv`

---

## Directory Structure

```text
django/Harsh/
├── manage.py                     # Django management script
├── requirements.txt              # Production and development dependencies
├── .env                          # Local environment variables (ignored by git)
├── .env.example                  # Template environment variables
├── .gitignore                    # Standard Python/Django git ignore rules
├── README.md                     # Project documentation & guidelines
├── Harsh/                        # Project configuration package
│   ├── __init__.py
│   ├── asgi.py                   # ASGI entrypoint
│   ├── settings.py               # Application settings & environment loading
│   ├── urls.py                   # Central URL routing
│   └── wsgi.py                   # WSGI entrypoint
└── core/                         # Main application package
    ├── __init__.py
    ├── admin.py                  # Standard Django admin configuration
    ├── apps.py                   # AppConfig declaration
    ├── context_processors.py     # Global layout context (cart count, role)
    ├── email_utils.py            # Transactional email dispatchers
    ├── forms.py                  # Model forms & input validators
    ├── middleware.py             # User deactivation session middleware
    ├── models.py                 # Database models
    ├── tests.py                  # Unit and integration test suite
    ├── validators.py             # File and security validators
    ├── views.py                  # View controllers
    ├── migrations/               # Database migrations
    ├── static/core/              # Static assets (style.css, images)
    └── templates/                # HTML templates extending base.html
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (recommended Python 3.12 - 3.14)
- Git

### 2. Environment Setup
Create and activate a virtual environment:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

Install project dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the example environment file and configure credentials:
```bash
cp .env.example .env
```

Configure your `.env` variables:
- `SECRET_KEY`: Secure secret key for Django.
- `DEBUG`: Set to `True` for development, `False` for production.
- `EMAIL_HOST_USER` & `EMAIL_HOST_PASSWORD`: Google App Password for outbound email. If left empty, emails print directly to the server terminal.
- `RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET`: Razorpay API credentials.

### 4. Database Migrations
Apply database migrations:
```bash
python manage.py migrate
```

### 5. Running the Application
Start the local development server:
```bash
python manage.py runserver
```
Access the application at `http://127.0.0.1:8000/`.

---

## Running Tests

The test suite covers models, forms, authentication, payment verification, and view controllers:
```bash
python manage.py test core
```

---

## Development Standards & Architecture Guidelines

To maintain clean code quality across future development:

1. **Self-Documenting Code**: Write clear, descriptive function, variable, and class names. Avoid redundant comments that simply state what code does (e.g. avoid `# save object` before `.save()`). Use docstrings only for non-trivial public interfaces.
2. **Separation of Concerns**:
   - **Models**: Keep database logic, calculated properties, and data constraints in `models.py`.
   - **Forms**: Place all input sanitization, clean methods, and file validation in `forms.py`.
   - **Views**: Handle HTTP request processing, authorization checks, and template rendering in `views.py`.
   - **Email**: Place all outbound email message assembly in `email_utils.py`.
3. **Template Conventions**:
   - All templates extend `base.html` or `admin_base.html`.
   - Avoid HTML narrative comments (`<!-- ... -->`) for standard markup elements.
   - Ensure CSRF tokens (`{% csrf_token %}`) are present on all POST forms.
4. **CSS & Styling**:
   - Maintain centralized stylesheet tokens in `static/core/style.css`.
   - Use standard CSS comments without ASCII divider banners.
   - When updating stylesheets in development, bump the version query parameter in `base.html` (e.g. `style.css?v=X.X`) to prevent stale browser caching.
