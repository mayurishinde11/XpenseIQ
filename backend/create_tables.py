# create_tables.py
# This is a one-time script that creates all our tables
# in the PostgreSQL database on Supabase.
# We run this once, and never need to run it again
# unless we add new tables.

# We import Base and engine from database.py
from database import Base, engine

# We import the models so SQLAlchemy knows about them
# If we don't import them, SQLAlchemy doesn't know
# these tables need to be created
from models.user import User
from models.expense import Expense

print("Creating tables...")

# create_all() looks at every class that inherits from Base
# and creates its table in the database
# checkfirst=True means: only create the table if it doesn't
# already exist. Never delete existing data.
Base.metadata.create_all(bind=engine, checkfirst=True)

print("Tables created successfully!")
print("Tables in database:")
print("  - users")
print("  - expenses")