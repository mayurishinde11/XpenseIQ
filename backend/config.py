from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

if not DATABASE_URL:
    print("WARNING: DATABASE_URL is not set in .env")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY is not set in .env")