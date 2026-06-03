# expense.py
# This file defines the Expense table in our database.
# Every scanned receipt becomes one row in this table.

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Expense(Base):

    __tablename__ = "expenses"

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

    # When this record was created in our system
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationship() lets us access the user object from an expense
    # For example: expense.user.email
    # This doesn't create a new column - it's just a Python convenience
    user = relationship("User", backref="expenses")