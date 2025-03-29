# Hostage Negotiator Game

A text-based hostage negotiation simulation game built with Django where players can practice and improve their negotiation skills in various scenarios.

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## Quick Start

1. Clone the repository
```bash
git clone https://github.com/oyekamal/hostage-game/tree/main
cd hostage-negotiator
```

2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
Copy `.env.example` to `.env`:
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Then edit `.env` and add your Grok API key:
```
API_KEY=API_KEY_GROKs  # Replace with your actual Grok API key
```

5. Run database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Start the development server
```bash
python manage.py runserver
```

7. Access the application:
- Main application: `http://localhost:8000`
- Admin interface: `http://localhost:8000/admin`

## Default Admin Credentials

The application comes with a default admin user:
- Username: `admin`
- Email: `admin@gmail.com`
- Password: `admin`

You can use these credentials to log in to both the main application and the admin interface. It's recommended to change the password after first login.

To create additional superusers:
```bash
python manage.py createsuperuser
```

## Features

- User authentication system
- Multiple negotiation scenarios
- Real-time AI-powered responses using OpenAI
- Progress tracking and scoring system
- Promise tracking system
- Email notifications for password reset
- User statistics and game history

## Project Structure

```
hostage-negotiator/
├── game/                   # Main game application
│   ├── migrations/        # Database migrations
│   ├── templates/        # HTML templates
│   ├── static/          # Static files (CSS, JS)
│   ├── models.py        # Database models
│   ├── views.py         # View logic
│   └── urls.py          # URL routing
├── hostage_negotiator/    # Project settings
├── manage.py             # Django management script
├── requirements.txt      # Project dependencies
└── .env                 # Environment variables (not in repo)
```

## Testing

To run the test suite:
```bash
python manage.py test
```

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to your branch
5. Create a Pull Request

## License

[Your chosen license]

## Contact

[Your contact information]
