# XpenseIQ — AI-powered Smart Expense Bill Scanner

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45-red)
![Railway](https://img.shields.io/badge/Deployed-Railway-purple)

An enterprise-grade AI-powered expense management system that automatically extracts, classifies, and analyzes financial data from receipt images and PDFs using OCR and Large Language Models.

## Live Demo

- **Dashboard:** https://frontend-production-fdc9.up.railway.app
- **API Docs:** https://xpenseiq-production.up.railway.app/docs

## Features

- **OCR Pipeline** — Extracts text from receipt images (JPG, PNG, WEBP, TIFF, BMP) and PDFs using Tesseract
- **AI Extraction** — Groq LLaMA 3.3 70B extracts vendor name, amount, date, GSTIN, tax, payment method, and line items
- **Expense Classification** — Automatically categorizes expenses into 10 categories (Food, Travel, Health, etc.)
- **Fraud Detection** — 6-rule engine assigns fraud risk score (0.0–1.0) with duplicate detection
- **Multi-format Support** — Handles images and multi-page PDFs
- **GSTIN Extraction** — Extracts GST Identification Numbers for business expense tracking
- **Advanced Filtering** — Filter by vendor, category, date range, amount range, GSTIN
- **JWT Authentication** — Secure login with bcrypt password hashing
- **Dashboard** — Real-time charts showing spend by category and payment methods
- **CSV Export** — Download expense history as CSV
- **REST API** — Fully documented OpenAPI 3.1 specification

## Architecture

User uploads receipt image or PDF
↓
Streamlit Dashboard (frontend)
↓
FastAPI Backend (REST API)
↓
6-Stage AI Pipeline:
Stage 1 → Tesseract OCR extracts raw text
Stage 2 → Groq LLaMA extracts structured data
Stage 3 → Classifies expense category
Stage 4 → Fraud detection with 6 rules
Stage 5 → Saves to PostgreSQL database
Stage 6 → Flags high risk expenses for review
↓
PostgreSQL on Supabase (cloud database)


## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit (Python) |
| Backend | FastAPI + Uvicorn |
| AI/LLM | Groq API (LLaMA 3.3 70B) |
| OCR | Tesseract + pytesseract |
| PDF Processing | pdf2image + Poppler |
| Database | PostgreSQL (Supabase) |
| ORM | SQLAlchemy |
| Authentication | JWT (python-jose) + bcrypt |
| Containerization | Docker + docker-compose |
| Deployment | Railway |
| CI/CD | GitHub Actions |

## Getting Started

### Prerequisites

- Python 3.11+
- Tesseract OCR installed
- Poppler installed (for PDF support)
- PostgreSQL database (Supabase recommended)
- Groq API key (free at console.groq.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/Siddhi-3843/XpenseIQ.git
cd XpenseIQ

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### Configuration

Create a `.env` file in the root directory:
DATABASE_URL=your_postgresql_connection_string
GROQ_API_KEY=your_groq_api_key
SECRET_KEY=your_jwt_secret_key
### Run Locally

```bash
# Terminal 1 — Start backend
cd backend
uvicorn main:app --reload

# Terminal 2 — Start frontend
cd frontend
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Run with Docker

```bash
docker-compose up --build
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /auth/register | No | Create new account |
| POST | /auth/login | No | Login and get JWT token |
| GET | /auth/me | Yes | Get current user profile |
| POST | /expenses/scan-receipt | Yes | Upload and scan receipt |
| GET | /expenses/ | Yes | List expenses with filters |
| GET | /expenses/summary | Yes | Dashboard metrics |
| GET | /expenses/{id} | Yes | Get single expense detail |
| DELETE | /expenses/{id} | Yes | Delete an expense |

## Fraud Detection Rules

Our fraud engine checks 6 rules and assigns a cumulative risk score from 0.0 to 1.0:

1. **Low OCR confidence** — below 0.60 means receipt may be unclear or tampered
2. **Round amount** — amounts that are exact multiples of 1000 are suspicious
3. **Missing receipt number** — legitimate businesses always print receipt numbers
4. **Weekend B2B transaction** — office suppliers closed on weekends
5. **Duplicate detection** — same vendor and amount within 90-day window
6. **High value** — transactions above Rs 50,000 flagged for review

Risk score above 0.5 triggers manual review flag.

## Database Schema
users
id              PRIMARY KEY
email           UNIQUE NOT NULL
hashed_password NOT NULL
full_name
created_at
expenses
id                     PRIMARY KEY
user_id                FOREIGN KEY → users.id
vendor_name
total_amount
primary_category
subcategory
fraud_risk_score
is_duplicate
requires_manual_review
fraud_flags            JSON
extracted_data         JSON
raw_ocr_text
confidence_score
transaction_date
receipt_number
gstin
created_at

## Project Structure
XpenseIQ/
├── backend/
│   ├── models/
│   │   ├── expense.py       SQLAlchemy expense table
│   │   └── user.py          SQLAlchemy user table
│   ├── routers/
│   │   ├── auth_router.py   Login, register, JWT endpoints
│   │   ├── expense_router.py Scan, list, filter endpoints
│   │   └── report_router.py Report generation endpoints
│   ├── services/
│   │   ├── ocr_service.py   Tesseract OCR pipeline
│   │   ├── ai_service.py    Groq LLaMA integration
│   │   ├── fraud_service.py Fraud detection engine
│   │   └── auth_service.py  JWT token management
│   ├── schemas/
│   ├── config.py            Environment variable loader
│   ├── database.py          SQLAlchemy connection setup
│   └── main.py              FastAPI application entry point
├── frontend/
│   ├── pages/
│   └── app.py               Streamlit dashboard
├── tests/
│   ├── test_ocr.py
│   ├── test_ai.py
│   └── test_api.py
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── deploy.yml       GitHub Actions CI/CD
└── README.md

## CI/CD Pipeline

Every push to the main branch triggers GitHub Actions which:
1. Sets up Python 3.11
2. Installs all dependencies
3. Runs import verification tests
4. If tests pass, Railway auto-deploys the new version

## Cost Analysis

| Service | Plan | Cost |
|---|---|---|
| Groq API | Free tier | Rs 0/month |
| Supabase PostgreSQL | Free tier | Rs 0/month |
| Railway hosting | Free tier | Rs 0/month |
| Tesseract OCR | Open source | Rs 0/month |
| **Total** | | **Rs 0/month** |

## Interview Topics This Project Covers

- Microservices architecture and service separation
- OCR pipeline design and image preprocessing
- LLM integration and prompt engineering
- JWT authentication and token-based security
- Database schema design with foreign key relationships
- Fraud detection algorithm design
- Docker containerization and multi-service orchestration
- CI/CD with GitHub Actions
- Cloud deployment on Railway
- REST API design with OpenAPI specification
- Production error handling and logging

## Author

Mayuri Shinde
- GitHub: https://github.com/Siddhi-3843
- Project: XpenseIQ — AI Expense Scanner