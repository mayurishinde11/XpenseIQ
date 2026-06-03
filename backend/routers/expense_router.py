# expense_router.py
# This file contains all the API routes related to expenses.
# Routes are the URLs that our frontend calls.
# For example: POST /expenses/scan-receipt

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.ocr_service import extract_text_from_image

# APIRouter creates a group of related routes
# prefix means all routes in this file start with /expenses
# tags groups them together in the API docs page
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
    Accepts an image upload and extracts text using OCR.
    
    UploadFile = FastAPI's way of receiving file uploads
    File(...) = this field is required (... means required)
    Depends(get_db) = automatically gives us a database session
    """

    # Step 1 — Validate the file type
    # We only accept image files for now
    # file.content_type contains the MIME type of the uploaded file
    # e.g. "image/jpeg", "image/png", "application/pdf"
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    
    if file.content_type not in allowed_types:
        # HTTPException sends an error response back to the client
        # status_code=400 means "Bad Request" - the client sent wrong data
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not supported. Please upload JPG or PNG."
        )

    # Step 2 — Read the file bytes
    # await is used because reading files is an async operation
    # it means: wait for the file to be fully read before continuing
    image_bytes = await file.read()

    # Step 3 — Run OCR on the image
    ocr_result = extract_text_from_image(image_bytes)

    # Step 4 — Return the OCR result
    return {
        "status": "success",
        "filename": file.filename,
        "ocr_result": ocr_result
    }