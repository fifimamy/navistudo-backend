# navistudo-backend

Backend API for NaviStudo — academic-path guidance for Algerian secondary-school students.

## Quick Start

### Prerequisites
- Python 3.11+
- Windows (PowerShell), Linux, or macOS

### Setup

```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### Run the Development Server

```powershell
flask --app run run
# Or:
python run.py
```

The server starts at `http://localhost:5000`.

### Run Tests

```powershell
pytest -v
```

### Health Check Endpoint

```powershell
curl http://localhost:5000/api/v1/health
# Response: {"status": "ok"}
```

## Project Structure

```
navistudo-backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration classes
│   └── routes/
│       ├── __init__.py
│       └── health.py        # GET /api/v1/health
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   └── test_health.py       # Health endpoint tests
├── run.py                   # Entry point
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Dev dependencies
└── .gitignore
```

## Configuration

| Environment | Config Class | Use Case |
|-------------|--------------|----------|
| `development` | `DevelopmentConfig` | Local development (default) |
| `testing` | `TestingConfig` | Automated tests |
| `production` | `ProductionConfig` | Production deployment |

Set via `FLASK_ENV` environment variable.

## Next Milestones

- Database models and migrations
- Student profile & eligibility endpoints
- Recommendation matching algorithm
- AI integration for guidance
- Authentication & authorization
- Knowledge base API