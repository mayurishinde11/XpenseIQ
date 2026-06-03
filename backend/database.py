# database.py
# This file creates the connection between our Python app
# and the PostgreSQL database on Supabase.
# Every other file that needs the database will import from here.

# SQLAlchemy is our ORM - it translates Python into SQL
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# We import our DATABASE_URL from config.py
# config.py reads it from the .env file
from config import DATABASE_URL

# create_engine() creates the actual connection to the database
# Think of it as opening a phone line to the database
# pool_pre_ping=True means: before using a connection, check if
# it's still alive. If not, create a new one. This prevents
# errors when the database connection goes idle.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# SessionLocal is a factory that creates database sessions
# A session is like a conversation with the database
# You open a session, do your queries, then close it
SessionLocal = sessionmaker(
    autocommit=False,  # Don't save changes automatically
    autoflush=False,   # Don't send changes to DB until we say so
    bind=engine        # Use our engine (connection) we created above
)

# Base is the parent class that all our database models will inherit from
# When we create a model like "Expense", it extends Base
# This is how SQLAlchemy knows it's a database table
Base = declarative_base()

# get_db() is a function that gives us a database session
# We use it in our API routes whenever we need to talk to the database
# The "yield" keyword means: give the session to whoever asked for it,
# and when they're done, come back here and close it
# This pattern ensures the session is ALWAYS closed, even if an error occurs
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()