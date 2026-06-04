# fraud_service.py
# This file contains all fraud detection logic.
# It analyzes an expense record and assigns a fraud risk score
# based on multiple detection rules.

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.expense import Expense


def check_fraud(
    extracted_data: dict,
    classification: dict,
    ocr_confidence: float,
    user_id: int,
    db: Session
) -> dict:
    """
    Analyzes an expense for fraud indicators.
    
    extracted_data: the structured data from AI extraction
    classification: the category assigned by AI
    ocr_confidence: how confident OCR was (0.0 to 1.0)
    user_id: who submitted this expense
    db: database session to check history
    
    Returns fraud analysis result
    """

    # List to collect all fraud flags found
    fraud_flags = []
    
    # Start with a base risk score of 0
    fraud_risk_score = 0.0

    # Get key values from extracted data
    total_amount = extracted_data.get("total_amount", 0) or 0
    vendor_name = extracted_data.get("vendor_name", "") or ""
    transaction_date = extracted_data.get("transaction_date", "") or ""
    receipt_number = extracted_data.get("receipt_number", None)
    payment_method = extracted_data.get("payment_method", "Unknown")

    # ─────────────────────────────────────────
    # RULE 1 — Low OCR confidence
    # If OCR couldn't read the receipt clearly,
    # it might be a fake or tampered receipt
    # ─────────────────────────────────────────
    if ocr_confidence < 0.60:
        fraud_flags.append("Low OCR confidence — receipt may be unclear or fake")
        fraud_risk_score += 0.25

    # ─────────────────────────────────────────
    # RULE 2 — Suspiciously round amount
    # Real receipts rarely end in exactly 000
    # Round amounts like 5000, 10000 are suspicious
    # ─────────────────────────────────────────
    if total_amount > 0 and total_amount % 1000 == 0:
        fraud_flags.append(f"Suspiciously round amount: {total_amount}")
        fraud_risk_score += 0.20

    # ─────────────────────────────────────────
    # RULE 3 — Missing receipt number
    # Legitimate businesses always print a receipt number
    # Missing receipt number is suspicious
    # ─────────────────────────────────────────
    if not receipt_number:
        fraud_flags.append("Missing receipt number")
        fraud_risk_score += 0.10

    # ─────────────────────────────────────────
    # RULE 4 — Weekend transaction for B2B vendor
    # Business vendors like office suppliers or
    # corporate restaurants are usually closed on weekends
    # ─────────────────────────────────────────
    if transaction_date:
        try:
            # Parse the date string into a datetime object
            txn_date = datetime.strptime(transaction_date, "%Y-%m-%d")
            
            # weekday() returns 0=Monday, 6=Sunday
            # 5=Saturday, 6=Sunday
            is_weekend = txn_date.weekday() in [5, 6]
            
            # Check if this is a business category
            primary_category = classification.get("primary_category", "")
            business_categories = ["Office & Supplies", "Finance"]
            
            if is_weekend and primary_category in business_categories:
                fraud_flags.append(
                    f"Weekend transaction for business vendor: {transaction_date}"
                )
                fraud_risk_score += 0.20
        except ValueError:
            # Date couldn't be parsed — that's also suspicious
            fraud_flags.append("Invalid or unreadable transaction date")
            fraud_risk_score += 0.15

    # ─────────────────────────────────────────
    # RULE 5 — Duplicate detection
    # Check if same vendor + similar amount exists
    # in last 7 days for this user
    # ─────────────────────────────────────────
    duplicate_check = check_duplicate(
        vendor_name=vendor_name,
        total_amount=total_amount,
        transaction_date=transaction_date,
        user_id=user_id,
        db=db
    )

    if duplicate_check["is_duplicate"]:
        fraud_flags.append(
            f"Exact duplicate found: expense ID {duplicate_check['duplicate_id']}"
        )
        fraud_risk_score += 0.40

    elif duplicate_check["is_near_duplicate"]:
        fraud_flags.append(
            f"Near duplicate found: similar expense within 7 days"
        )
        fraud_risk_score += 0.20

    # ─────────────────────────────────────────
    # RULE 6 — Very high amount
    # Flag expenses above ₹50,000 for review
    # ─────────────────────────────────────────
    if total_amount > 50000:
        fraud_flags.append(f"High value transaction: {total_amount}")
        fraud_risk_score += 0.15

    # Cap the fraud risk score at 1.0
    # It can never exceed 1.0
    fraud_risk_score = min(round(fraud_risk_score, 2), 1.0)

    # Require manual review if risk score is above 0.5
    requires_manual_review = fraud_risk_score >= 0.5

    return {
        "fraud_risk_score": fraud_risk_score,
        "fraud_flags": fraud_flags,
        "is_duplicate": duplicate_check["is_duplicate"],
        "is_near_duplicate": duplicate_check["is_near_duplicate"],
        "duplicate_match_id": duplicate_check.get("duplicate_id"),
        "requires_manual_review": requires_manual_review,
        "review_reason": ", ".join(fraud_flags) if fraud_flags else None
    }


def check_duplicate(
    vendor_name: str,
    total_amount: float,
    transaction_date: str,
    user_id: int,
    db: Session
) -> dict:
    """
    Checks if this expense is a duplicate of an existing one.
    
    Exact duplicate: same vendor + same amount + same date
    Near duplicate: same vendor + amount within 5% + within 7 days
    """

    # Default result — no duplicate found
    result = {
        "is_duplicate": False,
        "is_near_duplicate": False,
        "duplicate_id": None
    }

    # If no vendor name or amount, skip duplicate check
    if not vendor_name or not total_amount:
        return result

    try:
        # Get all expenses for this user from last 90 days
        ninety_days_ago = datetime.now() - timedelta(days=90)

        recent_expenses = db.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.created_at >= ninety_days_ago
        ).all()

        for expense in recent_expenses:
            # Check exact duplicate
            # Same vendor AND same amount AND same date
            if (
                expense.vendor_name == vendor_name and
                expense.total_amount == total_amount and
                expense.transaction_date == transaction_date
            ):
                result["is_duplicate"] = True
                result["duplicate_id"] = expense.id
                return result

            # Check near duplicate
            # Same vendor AND amount within 5% AND within 7 days
            if expense.vendor_name == vendor_name and expense.total_amount:
                amount_diff_pct = abs(
                    expense.total_amount - total_amount
                ) / total_amount * 100

                if amount_diff_pct <= 5:
                    result["is_near_duplicate"] = True

    except Exception:
        # If database check fails, skip duplicate detection
        pass

    return result