# user.py
# This file defines the User table in our database.
# Every person who registers on ExpenseIQ gets a row in this table.

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

# User class represents the "users" table in PostgreSQL
# It inherits from Base - this is how SQLAlchemy knows
# this class is a database table, not just a regular class
class User(Base):

    # __tablename__ tells SQLAlchemy what to name the table
    # in the actual database
    __tablename__ = "users"

    # Each Column() call creates one column in the table

    # id is the primary key - every row gets a unique number
    # autoincrement means PostgreSQL assigns the number automatically
    # 1, 2, 3, 4... you never set this manually
    id = Column(Integer, primary_key=True, autoincrement=True)

    # email must be unique - no two users can have the same email
    # nullable=False means this field is required, cannot be empty
    email = Column(String, unique=True, nullable=False, index=True)

    # We never store real passwords - always store the hashed version
    # index=True on email means PostgreSQL creates an index on this column
    # so searching by email is extremely fast even with millions of rows
    hashed_password = Column(String, nullable=False)

    # full_name is optional - nullable=True means it can be empty
    full_name = Column(String, nullable=True)

    # created_at stores when the user registered
    # server_default=func.now() means PostgreSQL automatically
    # fills this with the current timestamp when a new row is inserted
    # You never need to set this manually
    created_at = Column(DateTime(timezone=True), server_default=func.now())