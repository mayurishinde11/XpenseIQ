# expense_router.py
# This file contains all expense-related API routes.
# The scan-receipt route now runs the full pipeline:
# image upload → OCR → AI extraction → AI classification → response

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.ocr_service import extract_text_from_image
from services.ai_service import extract_expense_data, classify_expense

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
    Full pipeline: image → OCR → AI extraction → classification
    Returns structured expense data ready to save.
    """

    # Step 1 — Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not supported. Please upload JPG or PNG."
        )

    # Step 2 — Read image bytes
    image_bytes = await file.read()

    # Step 3 — Run OCR
    # This converts the image into raw text
    ocr_result = extract_text_from_image(image_bytes)

    # Step 4 — Check if OCR got any text
    # If confidence is too low or no text was found,
    # we return an error instead of sending garbage to AI
    if ocr_result["word_count"] < 3:
        raise HTTPException(
            status_code=422,
            detail="Could not extract enough text from image. Please upload a clearer image."
        )

    # Step 5 — Run AI extraction on the OCR text
    # This converts raw text into structured JSON
    ai_result = extract_expense_data(ocr_result["cleaned_text"])

    if ai_result["status"] == "error":
        raise HTTPException(
            status_code=500,
            detail=f"AI extraction failed: {ai_result['error']}"
        )

    # Step 6 — Run AI classification
    # This assigns a category to the expense
    extracted_data = ai_result["data"]

    classification_result = classify_expense(
        vendor_name=extracted_data.get("vendor_name", "Unknown"),
        line_items=extracted_data.get("line_items", []),
        vendor_hint=extracted_data.get("vendor_category_hint", None)
    )

    # Step 7 — Combine everything into one response
    final_result = {
        "status": "success",
        "filename": file.filename,
        "ocr": {
            "confidence_score": ocr_result["confidence_score"],
            "word_count": ocr_result["word_count"]
        },
        "extracted_data": extracted_data,
        "classification": classification_result.get("data", {})
    }

    return final_result