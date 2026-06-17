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

    fraud_flags = []
    fraud_risk_score = 0.0

    total_amount = extracted_data.get("total_amount", 0) or 0
    vendor_name = extracted_data.get("vendor_name", "") or ""
    transaction_date = extracted_data.get("transaction_date", "") or ""
    receipt_number = extracted_data.get("receipt_number", None)

    # RULE 1 — Low OCR confidence
    if ocr_confidence < 0.60:
        fraud_flags.append("Low OCR confidence — receipt may be unclear or fake")
        fraud_risk_score += 0.25

    # RULE 2 — Suspiciously round amount
    if total_amount > 0 and total_amount % 1000 == 0:
        fraud_flags.append(f"Suspiciously round amount: ₹{total_amount}")
        fraud_risk_score += 0.20

    # RULE 3 — Missing receipt number
    if not receipt_number:
        fraud_flags.append("Missing receipt number")
        fraud_risk_score += 0.10

    # RULE 4 — Weekend transaction for B2B vendor
    if transaction_date:
        try:
            txn_date = datetime.strptime(transaction_date, "%Y-%m-%d")
            is_weekend = txn_date.weekday() in [5, 6]
            primary_category = classification.get("primary_category", "")
            business_categories = ["Office & Supplies", "Finance"]
            if is_weekend and primary_category in business_categories:
                fraud_flags.append(
                    f"Weekend transaction for business vendor on {transaction_date}"
                )
                fraud_risk_score += 0.20
        except ValueError:
            fraud_flags.append("Invalid or unreadable transaction date")
            fraud_risk_score += 0.15

    # RULE 5 — Duplicate detection
    duplicate_check = check_duplicate(
        vendor_name=vendor_name,
        total_amount=total_amount,
        transaction_date=transaction_date,
        receipt_number=receipt_number,
        user_id=user_id,
        db=db
    )

    if duplicate_check["is_duplicate"]:
        fraud_flags.append(
            f"DUPLICATE BILL DETECTED — This bill is an exact copy of "
            f"Expense ID #{duplicate_check['duplicate_id']} "
            f"already submitted on {duplicate_check['duplicate_date']}"
        )
        fraud_risk_score += 0.60

    elif duplicate_check["is_near_duplicate"]:
        fraud_flags.append(
            f"POSSIBLE DUPLICATE — A very similar bill from the same vendor "
            f"was submitted recently (Expense ID #{duplicate_check['duplicate_id']}). "
            f"Please verify this is not a duplicate submission."
        )
        fraud_risk_score += 0.35

    # RULE 6 — High value transaction
    if total_amount > 50000:
        fraud_flags.append(f"High value transaction: ₹{total_amount}")
        fraud_risk_score += 0.15

    fraud_risk_score = min(round(fraud_risk_score, 2), 1.0)
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
    receipt_number: str,
    user_id: int,
    db: Session
) -> dict:

    result = {
        "is_duplicate": False,
        "is_near_duplicate": False,
        "duplicate_id": None,
        "duplicate_date": None
    }

    if not vendor_name or not total_amount:
        return result

    try:
        ninety_days_ago = datetime.now() - timedelta(days=90)

        recent_expenses = db.query(Expense).filter(
            Expense.user_id == user_id,
            Expense.created_at >= ninety_days_ago
        ).all()

        for expense in recent_expenses:
            if not expense.vendor_name:
                continue

            vendor_match = (
                expense.vendor_name.lower().strip() == vendor_name.lower().strip()
            )

            if not vendor_match:
                continue

            # Check 1 — Same receipt number = definite duplicate
            if (
                receipt_number and
                expense.receipt_number and
                receipt_number.strip() == expense.receipt_number.strip()
            ):
                result["is_duplicate"] = True
                result["duplicate_id"] = expense.id
                result["duplicate_date"] = str(expense.created_at)[:10]
                return result

            # Check 2 — Same vendor + same amount + same date = exact duplicate
            if (
                expense.total_amount == total_amount and
                expense.transaction_date == transaction_date
            ):
                result["is_duplicate"] = True
                result["duplicate_id"] = expense.id
                result["duplicate_date"] = str(expense.created_at)[:10]
                return result

            # Check 3 — Same vendor + amount within 5% = near duplicate
            if expense.total_amount:
                amount_diff_pct = abs(
                    expense.total_amount - total_amount
                ) / total_amount * 100

                if amount_diff_pct <= 5:
                    result["is_near_duplicate"] = True
                    result["duplicate_id"] = expense.id
                    result["duplicate_date"] = str(expense.created_at)[:10]

    except Exception:
        pass

    return result