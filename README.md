# navistudo-backend

Backend API for NaviStudo — academic-path guidance for Algerian secondary-school students.

## Overview

This is the backend skeleton for the NaviStudo platform, providing:

- Knowledge-base loading and validation (secondary branches + university majors)
- Student profile and questionnaire data
- Academic eligibility filtering (deterministic, rule-based)
- Model 1 and Model 2 AI pipeline (free-text extraction + ranking)
- Structured recommendation results
- API request and response validation
- Firebase Authentication and Firestore persistence
- Saving and retrieving student results
- Automated tests and integration contracts

**Current status**: MVP skeleton complete and testable with fake model clients. Real AI/Firebase integration available when credentials are provided.

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

### Environment Configuration

Copy the example environment file and fill in the required values:

```powershell
cp .env.example .env
```

Required environment variables are described below.

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

All 80 tests pass with fake model clients. Real AI/Firebase integration tests require credentials.

### Health Check Endpoint

```powershell
curl http://localhost:5000/api/v1/health
# Response: {"status": "ok"}
```

## Project Structure

```
navistudo-backend/
├── app/
│   ├── __init__.py          # Flask app factory (with CORS)
│   ├── config.py            # Configuration classes
│   ├── ai_provider.py       # Real/AI provider integration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py        # GET /api/v1/health
│   │   └── recommendations.py # POST/GET /api/v1/recommendations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── knowledge_base_service.py  # Old dataclass KB service
│   │   ├── knowledge_base_loader.py   # JSON loader with validation
│   │   ├── student_service.py         # Firebase student profiles
│   │   ├── results_service.py         # Firestore results persistence
│   │   └── recommendation_service.py  # Pipeline orchestration
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── firebase_client.py   # Firebase Admin SDK wrapper
│   │   ├── model_one.py           # Oumnia's Model 1 stub (DO NOT MODIFY)
│   │   └── model_two.py           # Oumnia's Model 2 stub (DO NOT MODIFY)
│   └── schemas/
│       ├── knowledge_base_schema.py  # Pydantic models for KB
│       ├── model_one_schema.py       # Model 1 input/output
│       ├── model_two_schema.py       # Model 2 input/output
│       └── recommendation_schema.py  # API request/response schemas
├── data/
│   └── knowledge_base/
│       ├── secondary_branches.json  # 6 Algerian secondary branches
│       ├── university_majors.json   # 5 Algerian university majors (new)
│       └── sources.json             # 11 source references
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_health.py       # Health endpoint tests
│   ├── test_knowledge_base_service.py  # Eligibility tests
│   ├── test_pipeline_with_fakes.py     # Fake pipeline tests
│   ├── test_recommendation_validation.py # Model output validation
│   └── test_recommendations.py     # API endpoint tests
├── run.py                   # Entry point
├── requirements.txt         # Runtime dependencies
└── requirements-dev.txt     # Dev dependencies
```

## Configuration

| Environment | Config Class | Use Case |
|-------------|--------------|----------|
| `development` | `DevelopmentConfig` | Local development (default) |
| `testing` | `TestingConfig` | Automated tests |
| `production` | `ProductionConfig` | Production deployment |

Set via `FLASK_ENV` environment variable.

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FLASK_ENV` | Flask environment (`development`, `testing`, `production`) | Yes |
| `SECRET_KEY` | Flask session secret key | Yes |
| `FIREBASE_PROJECT_ID` | Firebase project ID | Yes (for Firestore) |
| `FIREBASE_CLIENT_EMAIL` | Firebase service account email | Yes (for Firestore) |
| `FIREBASE_PRIVATE_KEY` | Firebase private key (with `\n` literals) | Yes (for Firestore) |
| `AI_REAL_MODE` | Set to `1` or `true` to enable real AI mode | No (default: development/fake) |
| `AI_MODEL_ONE_API_KEY` | API key for Model 1 provider | No (required if `AI_REAL_MODE=1`) |
| `AI_MODEL_TWO_API_KEY` | API key for Model 2 provider | No (required if `AI_REAL_MODE=1`) |
| `OPENAI_API_KEY` | Fallback OpenAI API key | No |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | No (default: `*`) |
| `AI_MODEL_ONE_NAME` | Model name for Model 1 (e.g., `gpt-4o-mini`) | No (default: `gpt-4o-mini`) |
| `AI_MODEL_TWO_NAME` | Model name for Model 2 (e.g., `gpt-4o-mini`) | No (default: `gpt-4o-mini`) |
| `AI_MODEL_ONE_TEMPERATURE` | Temperature for Model 1 | No (default: `0.0`) |
| `AI_MODEL_TWO_TEMPERATURE` | Temperature for Model 2 | No (default: `0.0`) |
| `AI_MODEL_ONE_TIMEOUT` | Request timeout in seconds for Model 1 | No (default: `30`) |
| `AI_MODEL_TWO_TIMEOUT` | Request timeout in seconds for Model 2 | No (default: `30`) |
| `AI_MODEL_ONE_MAX_RETRIES` | Max retries for Model 1 | No (default: `2`) |
| `AI_MODEL_TWO_MAX_RETRIES` | Max retries for Model 2 | No (default: `2`) |

### Development Mode (Default)

In development mode (default), the backend uses deterministic fake model clients that allow the full pipeline to be tested without AI credentials:

- `AI_REAL_MODE=0` (default): Fake clients used
- Knowledge base loads from JSON files
- Eligibility filtering uses deterministic rules
- Recommendations returned from fake Model 2
- Results saved via fake persistence (in-memory for tests)

### Real AI Mode

Set `AI_REAL_MODE=1` and provide the required API keys to enable real AI integration:

- Model 1: Free-text extraction via OpenAI or compatible provider
- Model 2: Ranking via OpenAI or compatible provider
- All outputs validated against Pydantic schemas
- Request timeouts, retries, and safe error handling
- Unknown/ineligible option IDs are rejected

## API Documentation

### Health Check

- **GET** `/api/v1/health`
- No authentication required
- Response: `{"status": "ok"}`

### Recommendations

- **POST** `/api/v1/recommendations`
  - Requires: `Authorization: Bearer <Firebase ID token>`
  - Creates a new recommendation analysis for the authenticated student
  - Returns: `201` with `RecommendationResponse` JSON
  - Errors: `401` (auth), `503` (Model 1/2 unavailable), `500` (validation error)

- **GET** `/api/v1/recommendations/<analysis_id>`
  - Requires: `Authorization: Bearer <Firebase ID token>`
  - Retrieves a previous recommendation result
  - Returns: `200` with `RecommendationResponse` JSON
  - Errors: `401` (auth), `403` (different student), `404` (not found), `503` (not implemented)

### Request Format (POST)

The frontend submits its questionnaire payload in the request body. The
student is identified by the Firebase ID token, **never** by a UID in the body.

```json
{
  "student_profile": {
    "current_stage_id": "third_secondary",
    "wilaya_code": "16",
    "subject_performance": [
      {"subject_id": "mathematics", "min_score": 14.5, "max_score": 16.0}
    ]
  },
  "interests": {
    "academic_interests": ["mathematics", "physics"],
    "career_interests": ["software_engineering"]
  },
  "future_direction": {
    "short_term_goals": ["complete secondary school"],
    "long_term_goals": ["study computer science"]
  },
  "problem_preferences": {
    "abstract_concrete_preference": "concrete",
    "human_vs_system_preference": "system"
  }
}
```

An empty body (`{}`) is still accepted for backward compatibility; the profile
is then read from Firestore. The verified token UID is always used, even if a
`student_uid` field is present in the body.

> The exact field names are being confirmed with the frontend team. The backend
> preserves unknown fields rather than rejecting them. See
> `docs/PAYLOAD_NOTES.md` for the current assumptions and mapping decisions.

### Response Format (Success)

```json
{
  "analysis_id": "uuid-string",
  "student_uid": "firebase-uid",
  "recommendation_type": "university_major",
  "recommendations": [
    {
      "id": "major_medicine",
      "option_id": "major_medicine",
      "name": "Médecine",
      "description": "Formation médicale générale...",
      "rank": 1,
      "score": 0.95,
      "reasoning": "Strong match based on sciences branch and grades"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "model_one_metadata": {...},
  "model_two_metadata": {...},
  "profile_saved": true
}
```

### Error Format

```json
{
  "error": "model_one_unavailable",
  "message": "Free-text analysis service is not available",
  "details": {"reason": "Model 1 not configured"}
}
```

## Knowledge Base

The knowledge base consists of validated JSON files:

| File | Records | Description |
|------|---------|-------------|
| `data/knowledge_base/secondary_branches.json` | 6 | Pre-existing: 6 Algerian secondary school branches with eligibility rules, matching metadata, and source references |
| `data/knowledge_base/university_majors.json` | 5 | Newly created: 5 university majors (Medicine, Computer Science, Engineering, Law, Economics) with eligibility criteria, matching metadata, and source references |
| `data/knowledge_base/sources.json` | 11 | Source references for audit trail |

### Eligibility Filtering

Deterministic rule-based filtering (not AI-dependent):

- **Branch requirements**: Student's current branch must match required branches
- **Wilaya requirements**: Student's wilaya must match required wilayas
- **Grade requirements**: Student's grades must meet minimum thresholds
- **Unknown status**: Never silently interpreted as "allowed"

### Knowledge-Base Data Status

The current records are an **illustrative sample**, not an official catalogue:

- The 6 secondary branches reflect the standard Algerian streams.
- The 5 university majors are representative examples.
- Branch/grade requirements are **not** official admission cutoffs and must not
  be treated as guaranteed eligibility. No official Algerian admission rule has
  been verified yet; the `verified` markers reflect internal review only.

**Subject-ID compatibility gap (important):** the frontend reports subject IDs
such as `mathematics`, `physics`, `french`, while the knowledge base uses codes
such as `mathematiques`, `physique_chimie`, `francais`. There is currently **zero
overlap**, so grade-based eligibility cannot match frontend subjects until a
mapping is agreed. The adapter preserves the raw `subject_id` and does **not**
invent a mapping. See `docs/PAYLOAD_NOTES.md`.

### AI Pipeline

Two-stage process:

1. **Model 1** (Free-text Extraction): Processes student's free-text answers and extracts structured semantic data
   - Input: `free_text_answers`, `question_context`, `school_year`, `current_branch`
   - Output: `extracted_data`, `metadata`, `success` flag
   - Uses either fake client (development) or real AI provider (configured)

2. **Model 2** (Ranking): Ranks eligible academic options based on student profile + Model 1 output
   - Input: `student_profile`, `model_one_output`, `eligible_options`, `recommendation_type`
   - Output: `ranked_recommendations` with `option_id`, `rank`, `score`, `reasoning`
   - Uses either fake client (development) or real AI provider (configured)
   - All option_ids validated against eligible list
   - Output validated by `recommendation_validation.py`

### Firebase Integration

- **Authentication**: Firebase ID token verification via `Authorization: Bearer <token>` header
- **Firestore collections**: 
  - `students` - Student profiles (uid, school_year, current_branch, wilaya, grades, free_text_answers, question_context, questionnaire)
  - `recommendation_results` - Saved recommendation analyses (analysis_id, student_uid, recommendations, metadata)
- **Ownership enforcement**: Results can only be retrieved by their authorized owner (student_uid must match)
- **Persistence on submit**: `POST /api/v1/recommendations` persists the submitted questionnaire to `students/{uid}` before running the pipeline

### Frontend Integration Contract

The frontend lives in a separate repository (React + Vite + Tailwind). Its
authoritative contract is `src/types/contract.ts`; the API call is in
`src/services/api.ts`.

**Request envelope** (`RecommendationRequestEnvelope`):
```
{
  "schema_version": "1.0.0",
  "student_profile": {
    "current_stage_id": "first_year_secondary" | "third_year_secondary",
    "current_study_group_id"?: "science_and_technology" | "arts_and_humanities",
    "current_branch_id"?: "experimental_sciences" | "mathematics" | "mathematical_technique"
                        | "management_and_economics" | "foreign_languages" | "literature_and_philosophy",
    "subject_performance": [{ "subject_id": "mathematics", "min_score": 14.5, "max_score": 16.0 }],
    "has_taken_baccalaureate": boolean,
    "baccalaureate_average": number | null,
    "subject_preference_order": ["mathematics"],
    "difficult_subject_ids": ["physics_chemistry"]
  },
  "interests": {
    "field_interest_levels": [{ "field_id": "computer_science_ai", "interest_level": 5 }],
    "selected_topic_ids": [], "curiosity_field_ids": [], "curiosity_topic_ids": [],
    "activity_ids": [], "work_environment_ids"?: [],
    "topic_other_text"?: { "question": "...", "answer": "..." },
    "target_role_text"?: { "question": "...", "answer": "..." }
  },
  "future_direction": {
    "goal_clarity": "clear_goal" | "general_direction" | "no_defined_goal",
    "target_field_ids"?: [], "considered_field_ids"?: [], "motivation_ids"?: [],
    "priority_ids"?: [], "alternative_field_ids"?: [], "field_discovery_levels"?: [],
    "goal_flexibility"?: number
  },
  "problem_preferences"?: {   // third year only
    "problem_type_ids": [], "theory_application_preference": 3,
    "abstract_concrete_preference": 3, "human_system_preference": 3
  }
}
```

**Response envelope** (backend now returns the frontend fields in addition to
its internal fields):
```
{
  "schema_version": "1.0.0",
  "recommendations": [
    {
      "major_id": "...", "title_en": "...", "title_ar": "...",
      "category": "engineering" | "health" | "science" | "humanities" | "business",
      "match_score": 0-100, "match_level": "strong_match" | "great_alternative" | "field_to_explore",
      "explanation_en": "...", "explanation_ar": "...",
      "key_subjects": [], "typical_careers": [], "prerequisite_branches": [],
      "min_indicative_average": null, "study_duration_years": null, "institution_types": []
    }
  ],
  "summary": { "primary_strength": "...", "suggested_focus": "...", "total_evaluated": 11 },
  "analysis_id": "...", "student_uid": "...", "recommendation_type": "...",
  "created_at": "...", "profile_saved": true
}
```

**ID mappings implemented in the backend adapter** (`app/services/frontend_adapter.py`):
stage ids, branch ids and subject ids are mapped to the knowledge-base codes
used by eligibility. Reverse mappings are applied when building the response.

**Required frontend configuration**:
- `VITE_API_URL=http://localhost:5000` (local) or the deployed backend URL
- The backend must allow the frontend origin via `CORS_ORIGINS`

#### Known integration blockers (require a decision)

1. **Authentication** — the frontend sends **no `Authorization` header** and has
   no Firebase dependency; the backend requires a Firebase ID token. Every
   request currently returns `401`, so the frontend silently falls back to its
   local recommendation engine. A decision is needed: add Firebase Auth to the
   frontend, or define a non-Firebase auth mechanism.
2. **Major-ID taxonomy** — the backend knowledge base uses ids such as
   `major_computer_science`, `major_law`, `major_economics`; the frontend
   `MAJORS_DATABASE` uses `major_computer_science_ai`, `major_law_diplomacy`,
   `major_finance_business_management`, … The response `major_id` therefore
   will not match the frontend's detail modal unless the taxonomies are aligned.
3. **Missing knowledge-base data** — `study_duration_years`,
   `min_indicative_average` and `institution_types` are returned as `null`/empty
   because the backend KB does not store them. The frontend's results view
   renders `study_duration_years` directly, so it will show "null" until the KB
   is enriched.
4. **Feedback endpoint** — the frontend calls `POST /api/v1/feedback`, which the
   backend does not implement. The frontend currently simulates success.

### Deployment (Render)

A `render.yaml` blueprint is included. To deploy:

1. Set environment variables in the Render dashboard:
   - `FLASK_ENV=production`
   - `SECRET_KEY=<random>`
   - `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY`
   - `OPENAI_API_KEY`
   - `CORS_ORIGINS=https://your-frontend-domain.com`

2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn --bind 0.0.0.0:$PORT run:app`
4. Health check path: `/api/v1/health`

## Testing

- **141 unit/integration tests pass** with deterministic test doubles (no real Firebase or AI)
- Coverage includes: eligibility, KB loading, Model 1/2 contracts, validation, API auth/ownership, and the frontend payload flow
- Real AI/Firebase integration requires credentials and is not covered by the automated suite

## Known Limitations

- Real AI model integration requires `OPENAI_API_KEY` and a reachable OpenAI-compatible endpoint
- Firebase Firestore requires credential configuration
- Knowledge base contains a representative sample (not comprehensive); eligibility rules are not officially verified
- **Subject-ID mapping between frontend and KB is not yet agreed** (zero overlap) — grade-based eligibility will not match frontend subjects until this is resolved
- `docs/frontend_payload_sample.json` is a reconstructed fixture; the real frontend payload must replace it and the mapping decisions confirmed

## Next Milestones

- Confirm the exact frontend payload contract with the frontend team
- Agree a subject-ID mapping between the frontend and the knowledge base
- Obtain official Algerian eligibility rules and sources
- Expand the knowledge base with verified academic options
- Run the end-to-end flow against real Firebase and a real AI provider