# NaviStudo

**AI-Assisted Academic Guidance for Algerian Students**

NaviStudo is an academic guidance platform designed to help Algerian secondary school students explore suitable academic pathways based on their grades, interests, areas of difficulty, and future goals.

## The Problem

Choosing an academic path can be challenging for students who are unsure which options best match their abilities, interests, and ambitions. NaviStudo aims to make this process clearer by providing personalized, structured academic recommendations.

## How It Works

1. **Build an academic profile:** Students provide information about their academic performance, favorite and disliked subjects, areas of difficulty, and future goals.
2. **Analyze the profile:** The system processes the student's information using its academic knowledge base and AI-assisted recommendation workflow.
3. **Explore recommendations:** Students receive ranked academic options intended to help them understand and compare possible pathways.

NaviStudo is a decision-support tool, not a replacement for official academic guidance. Its recommendations should be checked against current Algerian education requirements.

## Current Status

NaviStudo has a working initial implementation and is still under development. Some features and workflows require further testing, debugging, and improvement. Our current priorities are improving system reliability, validating recommendations, refining the academic knowledge base, and strengthening the integration between the frontend and backend.

## Technology Stack

- **Frontend:** React, Vite, Tailwind CSS
- **Backend:** Python, Flask
- **Database and Authentication:** Firebase Authentication, Cloud Firestore
- **Academic Knowledge Base:** JSON
- **AI Integration:** OpenAI-compatible API
- **Development Tools:** OpenCode, Git, GitHub
- **Backend Deployment:** Render

## Running Locally

### Prerequisites

- Python and pip
- Node.js and npm
- Git
- Firebase project credentials and any required AI API configuration

### 1. Clone the Backend

```bash
git clone https://github.com/fifimamy/navistudo-backend.git
cd navistudo-backend
```

### 2. Set Up the Backend

Create and activate a Python virtual environment:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables and Firebase credentials according to the project's configuration and deployment requirements. Never commit credentials or secret keys.

Run the backend locally using Flask:

```bash
python -m flask --app "app:create_app()" run --debug
```

If your local configuration uses a different startup command, follow the instructions in the backend repository.

### 3. Set Up the Frontend

Clone the frontend repository and enter its directory:

```bash
git clone <FRONTEND_REPOSITORY_URL>
cd <FRONTEND_DIRECTORY>
```

Install the dependencies:

```bash
npm install --legacy-peer-deps
```

Configure the frontend environment variables using the project's environment example file, if available. Set the backend API URL to your local backend address and configure any required Firebase settings.

Start the development server:

```bash
npm run dev
```

Follow the local URL displayed in the terminal to open the application.

**Important:** The frontend and backend must be configured to communicate with each other. Firebase and AI features may require valid credentials and provider configuration to work locally.

## Backend API

The backend provides versioned API endpoints, including:

- `GET /api/v1/health` — checks backend availability.
- `POST /api/v1/recommendations` — submits a recommendation request.
- `GET /api/v1/recommendations/<analysis_id>` — retrieves a recommendation analysis by its identifier.

Access to protected endpoints may require a valid Firebase Authentication token.

## Team and Contributions

- **Oulfa Bouazdia — Project Lead & Backend Developer:** Led project planning and product definition, and worked on backend development, AI integration, data flow, and system improvements.
- **Faouzi Ait Addi — Frontend Developer:** Worked on frontend development and frontend-backend integration.
- **Anfal M’siouri — Knowledge Base Developer:** Built the project's academic knowledge base.
- **Mouna Benouda — Testing & Validation:** Tested the application and checked whether its workflows behaved as expected.

## Future Development

Our next steps include fixing existing issues, improving the reliability of data flow between components, expanding and validating the academic knowledge base, testing recommendation quality, and gathering feedback from Algerian students.

We aim to make NaviStudo a more reliable and useful resource for students exploring their academic futures.

---

**Project Repository:** https://github.com/fifimamy/navistudo-backend

NaviStudo is an ongoing project developed to support informed academic decision-making.