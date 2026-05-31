# config.py
# This file reads our secret values from the .env file
# and makes them available to the rest of the application

# python-dotenv is the package that knows how to read .env files
from dotenv import load_dotenv

# os is a built-in Python module that lets us read
# environment variables from the system
import os

# load_dotenv() opens the .env file and loads all the
# KEY=VALUE pairs into memory so os.getenv() can find them
load_dotenv()

# os.getenv() reads one variable by name from the environment
# The second argument is the default value if the variable is missing
DATABASE_URL = os.getenv("DATABASE_URL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

# These are simple warnings that print at startup
# if critical keys are missing from your .env file
if not DATABASE_URL:
    print("WARNING: DATABASE_URL is not set in .env")

if not ANTHROPIC_API_KEY:
    print("WARNING: ANTHROPIC_API_KEY is not set in .env")