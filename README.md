# XpenseIQ — AI-powered Smart Expense Bill Scanner

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.45-red)
![Railway](https://img.shields.io/badge/Deployed-Railway-purple)

An enterprise-grade AI-powered expense management system that automatically extracts, classifies, and analyzes financial data from receipt images and PDFs using OCR and Large Language Models.

## Live Demo

- **Dashboard:** https://radiant-tranquility-production.up.railway.app/
- **API Docs:** https://xpenseiq-production.up.railway.app/docs

## Features
OCR Pipeline — Extracts text from receipt images (JPG, PNG, WEBP, TIFF, BMP) and PDFs using VISION AI OCR
AI Extraction — Groq LLaMA 3.3 70B extracts vendor name, amount, date, GSTIN, tax, payment method, and line items
Expense Classification — Automatically categorizes expenses into 10 categories (Food, Travel, Health, etc.)
Fraud Detection — 6-rule engine assigns fraud risk score (0.0–1.0) with duplicate detection
Multi-format Support — Handles images and multi-page PDFs
GSTIN Extraction — Extracts GST Identification Numbers for business expense tracking
Advanced Filtering — Filter by vendor, category, date range, amount range, GSTIN
JWT Authentication — Secure login with bcrypt password hashing
Dashboard — Real-time charts showing spend by category and payment methods
CSV Export — Download expense history as CSV
REST API — Fully documented OpenAPI 3.1 specification
Architecture
User uploads receipt image or PDF ↓ Streamlit Dashboard (frontend) ↓ FastAPI Backend (REST API) ↓ 6-Stage AI Pipeline: Stage 1 → VISION AI OCR extracts raw text Stage 2 → Groq LLaMA extracts structured data Stage 3 → Classifies expense category Stage 4 → Fraud detection with 6 rules Stage 5 → Saves to PostgreSQL database Stage 6 → Flags high risk expenses for review ↓ PostgreSQL on Supabase (cloud database)

## Tech Stack
Layer	Technology
Frontend	Streamlit (Python)
Backend	FastAPI + Uvicorn
AI/LLM	Groq API (LLaMA 3.3 70B)
OCR	Vision AI
PDF Processing	pdf2image + Poppler
Database	PostgreSQL (Supabase)
ORM	SQLAlchemy
Authentication	JWT (python-jose) + bcrypt
Containerization	Docker + docker-compose
Deployment	Railway
CI/CD	GitHub Actions
Getting Started
Prerequisites
Python 3.11+
VISION AI OCR installed
Poppler installed (for PDF support)
PostgreSQL database (Supabase recommended)
Groq API key (free at console.groq.com)
Installation
 
# Clone the repository
git clone https://github.com/mayurishinde11/XpenseIQ
cd XpenseIQ

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
Configuration
Create a .env file in the root directory: DATABASE_URL=your_postgresql_connection_string GROQ_API_KEY=your_groq_api_key SECRET_KEY=your_jwt_secret_key

Run Locally
# Terminal 1 — Start backend
cd backend
uvicorn main:app --reload

# Terminal 2 — Start frontend
cd frontend
streamlit run app.py
Open http://localhost:8501 in your browser.

## Run with Docker
docker-compose up --build
API Endpoints
Method	Endpoint	Auth	Description
POST	/auth/register	No	Create new account
POST	/auth/login	No	Login and get JWT token
GET	/auth/me	Yes	Get current user profile
POST	/expenses/scan-receipt	Yes	Upload and scan receipt
GET	/expenses/	Yes	List expenses with filters
GET	/expenses/summary	Yes	Dashboard metrics
GET	/expenses/{id}	Yes	Get single expense detail
DELETE	/expenses/{id}	Yes	Delete an expense
Fraud Detection Rules
Our fraud engine checks 6 rules and assigns a cumulative risk score from 0.0 to 1.0:

## Project Structure
XpenseIQ/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models/
│   │   └── expense.py
│   ├── routers/
│   │   ├── auth_router.py
│   │   └── expense_router.py
│   └── services/
│       ├── ocr_service.py
│       ├── ai_service.py
│       └── fraud_service.py
├── frontend/
│   └── app.py
└── README.md

## 7-Rule Fraud Detection Engine
Low OCR confidence detection — below 0.60 means receipt may be unclear or tampered
Suspiciously round amount detection — amounts that are exact multiples of 1000 are suspicious
Missing receipt number — legitimate businesses always print receipt numbers
Weekend transaction For B2B Vendors — office suppliers closed on weekends
Duplicate detection — same vendor and amount within 90-day window
High-value transaction flagging — transactions above Rs 50,000 flagged for review
AI generated bills - if bills have wrong GSTIN number
Risk score above 0.3 triggers manual review flag.
Amount mismatch validation (subtotal + tax + charges vs total)

## Plus:

GSTIN format validation and live GST portal verification
AI-generated / fabricated invoice detection (8-signal scoring system)
Demo/test keyword detection

## Smart Approval Workflow

3-state automated routing: Approved → Pending Verification → Rejected
Risk-based routing:
0 – 29 → Auto-approved (Low risk)
30 – 69 → Manual review required (Medium risk)
70 – 100 → High risk, immediate review

## Real-Time Analytics Dashboard

Total spend, transaction count, pending/rejected counts
Category-wise and vendor-wise spend breakdown
AI-generated spending insights
Exportable reports (CSV / Excel)


## Email Notifications
Automatic approval/rejection emails sent to bill owners via SendGrid

## How It Works

Upload Receipt → OCR Extract → AI Validation → Fraud Check → Approval Routing → Analytics → Email Notification
Upload — receipt or invoice in any supported format
OCR Extract — Vision AI extracts vendor, amount, date, GSTIN, line items, and more
AI Validation — extracted data cross-checked for accuracy
Fraud Check — 7-rule engine + GSTIN verification + AI-fabrication detection
Approval — auto-approved, sent to pending review, or rejected based on risk score
Analytics — real-time dashboard updates
Email Notification — owner notified of approval/rejection automatically

## CI/CD Pipeline
Every push to the main branch triggers GitHub Actions which:

Sets up Python 3.11
Installs all dependencies
Runs import verification tests
If tests pass, Railway auto-deploys the new version

## Author

Mayuri Shinde
- GitHub: https://github.com/mayurishinde11
- Project: XpenseIQ — AI Expense Scanner

## Team Member

   Member               Role
Mayuri Shinde         Development
Siddhi Deshmukh       Development

## Guides
 Harshi Shah, Vishwajeet Sonkar


## Future Roadmap

AI Agents for autonomous claim handling
Predictive spend analytics
Mobile app (iOS / Android)
Budget intelligence with overspend alerts
ERP integrations (SAP, Oracle, NetSuite)
WhatsApp bot for expense submission


## Acknowledgements

We thank The Hg Foundation, Serrala Center of Excellence, Rotary Club of Bibwewadi, and Pune Institute of Computer Technology for their support throughout this journey.

Built for the Serrala AI Solutions Challenge 2026