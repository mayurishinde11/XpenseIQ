# expense.py
# This file defines the Expense table in our database.
# Every scanned receipt becomes one row in this table.
 
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from database import Base
 
class Expense(Base):
 
    __tablename__ = "expenses"
    __table_args__ = {'extend_existing': True} 
 
    # Primary key - unique ID for each expense
    id = Column(Integer, primary_key=True, autoincrement=True)
 
    # ForeignKey links this expense to the user who submitted it
    # "users.id" means: this value must exist in the id column of users table
    # This is the relationship between the two tables
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
 
    # Vendor information extracted by OCR + AI
    vendor_name = Column(String, nullable=True)
    vendor_category = Column(String, nullable=True)
 
    # Financial data
    total_amount = Column(Float, nullable=True)
    subtotal = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    tax_type = Column(String, nullable=True)
    currency_code = Column(String, default="INR")
 
    # Payment information
    payment_method = Column(String, nullable=True)
 
    # AI Classification results
    primary_category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)
    classification_confidence = Column(Float, nullable=True)
 
    # Fraud detection results
    fraud_risk_score = Column(Float, default=0.0)
    is_duplicate = Column(Boolean, default=False)
    requires_manual_review = Column(Boolean, default=False)
    fraud_flags = Column(JSON, nullable=True)
 
    # OCR and AI metadata
    raw_ocr_text = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    receipt_number = Column(String, nullable=True)
 
    # The complete AI extracted data stored as JSON
    extracted_data = Column(JSON, nullable=True)
 
    # Date of the actual transaction on the receipt
    transaction_date = Column(String, nullable=True)
        # Status of the expense
    # approved = clean bill, counted in totals
    # pending_verification = suspicious, awaiting review
    # rejected = rejected by admin, excluded from totals
    status = Column(String, default="approved", nullable=False)
    approved_by = Column(String, nullable=True)
 
    # When this record was created in our system
    created_at = Column(DateTime(timezone=True), server_default=func.now())
 
    # relationship() lets us access the user object from an expense
    # For example: expense.user.email
    # This doesn't create a new column - it's just a Python convenience
   
 
# user.py
# This file defines the User table in our database.
# Every person who registers on ExpenseIQ gets a row in this table.
 
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base
 
# User class represents the "users" table in PostgreSQL
# It inherits from Base - this is how SQLAlchemy knows
# this class is a database table, not just a regular class
# class User(Base):
 
#     # __tablename__ tells SQLAlchemy what to name the table
#     # in the actual database
#     __tablename__ = "users"
 
#     # Each Column() call creates one column in the table
 
#     # id is the primary key - every row gets a unique number
#     # autoincrement means PostgreSQL assigns the number automatically
#     # 1, 2, 3, 4... you never set this manually
#     id = Column(Integer, primary_key=True, autoincrement=True)
 
#     # email must be unique - no two users can have the same email
#     # nullable=False means this field is required, cannot be empty
#     email = Column(String, unique=True, nullable=False, index=True)
 
#     # We never store real passwords - always store the hashed version
#     # index=True on email means PostgreSQL creates an index on this column
#     # so searching by email is extremely fast even with millions of rows
#     hashed_password = Column(String, nullable=False)
 
#     # full_name is optional - nullable=True means it can be empty
#     full_name = Column(String, nullable=True)
 
#     # created_at stores when the user registered
#     # server_default=func.now() means PostgreSQL automatically
#     # fills this with the current timestamp when a new row is inserted
#     # You never need to set this manually
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
owner_email = Column(String, nullable=True)