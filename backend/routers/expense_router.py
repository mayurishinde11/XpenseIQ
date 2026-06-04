# expense_router.py
# Full pipeline: OCR → AI extraction → Fraud detection → Save to DB

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.ocr_service import extract_text_from_image
from services.ai_service import extract_expense_data, classify_expense
from services.fraud_service import check_fraud
from models.expense import Expense
from models.user import User
router = APIRouter(
    prefix="/expenses",
    tags=["Expenses"]
)


@router.post("/scan-receipt")
async def scan_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Full pipeline:
    1. Receive image upload
    2. Run OCR to extract text
    3. Run AI to extract structured data
    4. Run AI to classify expense
    5. Run fraud detection
    6. Save to database
    7. Return complete result
    """

    # Step 1 — Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not supported."
        )

    # Step 2 — Read image bytes
    image_bytes = await file.read()

    # Step 3 — Run OCR
    ocr_result = extract_text_from_image(image_bytes)

    if ocr_result["word_count"] < 3:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough text from image."
        )

    # Step 4 — Run AI extraction
    ai_result = extract_expense_data(ocr_result["cleaned_text"])

    if ai_result["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=f"AI extraction failed: {ai_result['error']}"
        )

    extracted_data = ai_result["data"]

    # Step 5 — Run AI classification
    classification_result = classify_expense(
        vendor_name=extracted_data.get("vendor_name", "Unknown"),
        line_items=extracted_data.get("line_items", []),
        vendor_hint=extracted_data.get("vendor_category_hint", None)
    )
    classification = classification_result.get("data", {})

    # Step 6 — Run fraud detection
    # For now we use user_id=1 as a placeholder
    # In Day 6 we will replace this with the real logged-in user
    fraud_result = check_fraud(
        extracted_data=extracted_data,
        classification=classification,
        ocr_confidence=ocr_result["confidence_score"],
        user_id=1,
        db=db
    )

    # Step 7 — Save to database
    # Create a new Expense object with all the extracted data
    new_expense = Expense(
        user_id=1,
        vendor_name=extracted_data.get("vendor_name"),
        vendor_category=extracted_data.get("vendor_category_hint"),
        total_amount=extracted_data.get("total_amount"),
        subtotal=extracted_data.get("subtotal"),
        tax_amount=extracted_data.get("tax_amount"),
        tax_type=extracted_data.get("tax_type"),
        currency_code=extracted_data.get("currency_code", "INR"),
        payment_method=extracted_data.get("payment_method"),
        primary_category=classification.get("primary_category"),
        subcategory=classification.get("subcategory"),
        classification_confidence=classification.get("classification_confidence"),
        fraud_risk_score=fraud_result["fraud_risk_score"],
        is_duplicate=fraud_result["is_duplicate"],
        requires_manual_review=fraud_result["requires_manual_review"],
        fraud_flags=fraud_result["fraud_flags"],
        raw_ocr_text=ocr_result["cleaned_text"],
        confidence_score=ocr_result["confidence_score"],
        receipt_number=extracted_data.get("receipt_number"),
        extracted_data=extracted_data,
        transaction_date=extracted_data.get("transaction_date")
    )

    # Add the new expense to the database session
    # This stages it for insertion
    db.add(new_expense)

    # Commit saves the staged changes to the database permanently
    db.commit()

    # Refresh loads the newly assigned ID from the database
    # back into our Python object
    db.refresh(new_expense)

    # Step 8 — Return complete result
    return {
        "status": "success",
        "expense_id": new_expense.id,
        "filename": file.filename,
        "ocr": {
            "confidence_score": ocr_result["confidence_score"],
            "word_count": ocr_result["word_count"]
        },
        "extracted_data": extracted_data,
        "classification": classification,
        "fraud_analysis": fraud_result
    }


@router.get("/")
def get_all_expenses(db: Session = Depends(get_db)):
    """
    Returns all expenses from the database.
    Later we will filter by logged-in user.
    """
    expenses = db.query(Expense).all()

    return {
        "status": "success",
        "count": len(expenses),
        "expenses": [
            {
                "id": e.id,
                "vendor_name": e.vendor_name,
                "total_amount": e.total_amount,
                "primary_category": e.primary_category,
                "transaction_date": e.transaction_date,
                "fraud_risk_score": e.fraud_risk_score,
                "requires_manual_review": e.requires_manual_review,
                "created_at": str(e.created_at)
            }
            for e in expenses
        ]
    }


@router.get("/{expense_id}")
def get_expense_by_id(expense_id: int, db: Session = Depends(get_db)):
    """
    Returns a single expense by its ID.
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()

    if not expense:
        raise HTTPException(
            status_code=404,
            detail=f"Expense with id {expense_id} not found"
        )

    return {
        "status": "success",
        "expense": {
            "id": expense.id,
            "vendor_name": expense.vendor_name,
            "total_amount": expense.total_amount,
            "primary_category": expense.primary_category,
            "subcategory": expense.subcategory,
            "transaction_date": expense.transaction_date,
            "fraud_risk_score": expense.fraud_risk_score,
            "fraud_flags": expense.fraud_flags,
            "requires_manual_review": expense.requires_manual_review,
            "extracted_data": expense.extracted_data,
            "created_at": str(expense.created_at)
        }
    }