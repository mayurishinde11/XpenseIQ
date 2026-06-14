
# #expense_router.py
# from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
# from sqlalchemy.orm import Session
# from database import get_db
# from services.ocr_service import extract_text_from_image, extract_text_from_pdf, validate_image_file
# from services.ai_service import extract_expense_data, classify_expense
# from services.fraud_service import check_fraud
# from models.expense import Expense
# from routers.auth_router import get_current_user

# router = APIRouter(
#     prefix="/expenses",
#     tags=["Expenses"]
# )


# # ─────────────────────────────────────────────────────────
# # HELPER FUNCTION
# # ─────────────────────────────────────────────────────────

# def build_expense_object(
#     user_id: int,
#     expense_status: str,
#     extracted_data: dict,
#     classification: dict,
#     fraud_result: dict,
#     ocr_result: dict
# ) -> Expense:
#     """
#     Creates an Expense database object from pipeline results.
#     Used by both single and bulk upload routes.
#     """
#     return Expense(
#         user_id=user_id,
#         status=expense_status,

#         # Vendor Information
#         vendor_name=extracted_data.get("vendor_name"),
#         vendor_category=extracted_data.get("vendor_category_hint"),

#         # Financial Data
#         total_amount=extracted_data.get("total_amount"),
#         subtotal=extracted_data.get("subtotal"),
#         tax_amount=extracted_data.get("tax_amount"),
#         tax_type=extracted_data.get("tax_type"),
#         currency_code=extracted_data.get("currency_code", "INR"),

#         # Payment Information
#         payment_method=extracted_data.get("payment_method"),

#         # AI Classification
#         primary_category=classification.get("primary_category"),
#         subcategory=classification.get("subcategory"),
#         classification_confidence=classification.get("classification_confidence"),

#         # Fraud Detection Results
#         fraud_risk_score=fraud_result["fraud_risk_score"],
#         is_duplicate=fraud_result["is_duplicate"],
#         requires_manual_review=fraud_result["requires_manual_review"],
#         fraud_flags=fraud_result["fraud_flags"],

#         # OCR Metadata
#         raw_ocr_text=ocr_result["cleaned_text"],
#         confidence_score=ocr_result["confidence_score"],

#         # Receipt Information
#         receipt_number=extracted_data.get("receipt_number"),
#         extracted_data=extracted_data,
#         transaction_date=extracted_data.get("transaction_date")
#     )


# def run_full_pipeline(
#     file_bytes: bytes,
#     content_type: str,
#     user_id: int,
#     db: Session
# ) -> dict:
#     """
#     Runs the complete AI pipeline on a single file.
#     Used by both single and bulk upload routes.
#     Returns a result dictionary.
#     """
#     image_types = [
#         "image/jpeg", "image/png", "image/jpg",
#         "image/webp", "image/tiff", "image/bmp"
#     ]
#     pdf_types = ["application/pdf"]

#     # Stage 1 — File Validation
#     validation = validate_image_file(file_bytes, content_type)
#     if not validation["is_valid"]:
#         return {"success": False, "error": validation["reason"]}

#     # Stage 2 — OCR
#     if content_type in pdf_types:
#         ocr_result = extract_text_from_pdf(file_bytes)
#     else:
#         ocr_result = extract_text_from_image(file_bytes)

#     if ocr_result.get("error"):
#         return {"success": False, "error": f"OCR failed: {ocr_result['error']}"}

#     if ocr_result["word_count"] < 3:
#         return {
#             "success": False,
#             "error": "Could not extract enough text. Please upload a clearer image."
#         }

#     # Stage 3 — AI Extraction
#     ai_result = extract_expense_data(ocr_result["cleaned_text"])

#     if ai_result["status"] == "error":
#         return {"success": False, "error": f"AI extraction failed: {ai_result['error']}"}

#     extracted_data = ai_result["data"]

#     # Stage 4 — Receipt Validity Check
#     total_amount = extracted_data.get("total_amount")
#     vendor_name = extracted_data.get("vendor_name")

#     if not total_amount and not vendor_name:
#         return {
#             "success": False,
#             "error": "This file does not appear to be a receipt or bill. No financial data found."
#         }

#     if not total_amount:
#         return {
#             "success": False,
#             "error": "Could not extract total amount. Please upload a clearer receipt."
#         }

#     # Stage 5 — AI Classification
#     classification_result = classify_expense(
#         vendor_name=extracted_data.get("vendor_name", "Unknown"),
#         line_items=extracted_data.get("line_items", []),
#         vendor_hint=extracted_data.get("vendor_category_hint", None)
#     )
#     classification = classification_result.get("data", {})

#     # Stage 6 — Fraud Detection
#     fraud_result = check_fraud(
#         extracted_data=extracted_data,
#         classification=classification,
#         ocr_confidence=ocr_result["confidence_score"],
#         user_id=user_id,
#         db=db
#     )

#     # Stage 7 — Determine Expense Status
#     if fraud_result["fraud_risk_score"] >= 0.5 or fraud_result["requires_manual_review"]:
#         expense_status = "pending_verification"
#     else:
#         expense_status = "approved"

#     return {
#         "success": True,
#         "extracted_data": extracted_data,
#         "classification": classification,
#         "fraud_result": fraud_result,
#         "ocr_result": ocr_result,
#         "expense_status": expense_status
#     }


# # ─────────────────────────────────────────────────────────
# # SINGLE RECEIPT SCAN
# # ─────────────────────────────────────────────────────────

# @router.post("/scan-receipt")
# async def scan_receipt(
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Scans a single receipt image or PDF.

#     Flow:
#     1. Validate file — reject blank/empty/invalid files
#     2. OCR — extract raw text
#     3. AI extraction — extract vendor, amount, date, GSTIN etc.
#     4. Receipt validity check — reject non-receipt files
#     5. AI classification — assign expense category
#     6. Fraud detection — check 6 fraud rules
#     7. Set status: approved or pending_verification
#     8. Save to database
#     """

#     allowed_types = [
#         "image/jpeg", "image/png", "image/jpg",
#         "image/webp", "image/tiff", "image/bmp",
#         "application/pdf"
#     ]

#     if file.content_type not in allowed_types:
#         raise HTTPException(
#             status_code=400,
#             detail=f"File type not supported. Please upload JPG, PNG, WEBP, TIFF, BMP, or PDF."
#         )

#     file_bytes = await file.read()

#     # Run full pipeline
#     pipeline_result = run_full_pipeline(
#         file_bytes=file_bytes,
#         content_type=file.content_type,
#         user_id=current_user.id,
#         db=db
#     )

#     if not pipeline_result["success"]:
#         raise HTTPException(
#             status_code=422,
#             detail=pipeline_result["error"]
#         )

#     extracted_data = pipeline_result["extracted_data"]
#     classification = pipeline_result["classification"]
#     fraud_result = pipeline_result["fraud_result"]
#     ocr_result = pipeline_result["ocr_result"]
#     expense_status = pipeline_result["expense_status"]

#     # Save to database
#     new_expense = build_expense_object(
#         user_id=current_user.id,
#         expense_status=expense_status,
#         extracted_data=extracted_data,
#         classification=classification,
#         fraud_result=fraud_result,
#         ocr_result=ocr_result
#     )

#     db.add(new_expense)
#     db.commit()
#     db.refresh(new_expense)

#     return {
#         "status": "success",
#         "expense_id": new_expense.id,
#         "expense_status": expense_status,
#         "filename": file.filename,
#         "file_type": file.content_type,
#         "ocr": {
#             "confidence_score": ocr_result["confidence_score"],
#             "word_count": ocr_result["word_count"],
#             "source": ocr_result.get("source", "image"),
#             "pages": ocr_result.get("pages", 1)
#         },
#         "extracted_data": extracted_data,
#         "classification": classification,
#         "fraud_analysis": fraud_result,
#         "message": (
#             "Receipt scanned and approved successfully"
#             if expense_status == "approved"
#             else "Receipt flagged for verification. Please review in the Pending Verification tab."
#         )
#     }


# # ─────────────────────────────────────────────────────────
# # BULK RECEIPT SCAN
# # ─────────────────────────────────────────────────────────

# @router.post("/scan-bulk")
# async def scan_bulk_receipts(
#     files: list[UploadFile] = File(...),
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Scans multiple receipts at once (maximum 10 files).

#     Each file goes through the full pipeline independently.
#     Returns a summary showing how many were approved,
#     pending verification, or failed.
#     """

#     if len(files) > 10:
#         raise HTTPException(
#             status_code=400,
#             detail="Maximum 10 files allowed per bulk upload. Please split into smaller batches."
#         )

#     allowed_types = [
#         "image/jpeg", "image/png", "image/jpg",
#         "image/webp", "image/tiff", "image/bmp",
#         "application/pdf"
#     ]

#     results = []
#     successful = 0
#     failed = 0
#     pending = 0

#     for file in files:
#         file_result = {
#             "filename": file.filename,
#             "status": None,
#             "expense_id": None,
#             "expense_status": None,
#             "error": None,
#             "vendor_name": None,
#             "total_amount": None,
#             "category": None,
#             "fraud_risk_score": None
#         }

#         try:
#             # Check file type
#             if file.content_type not in allowed_types:
#                 file_result["status"] = "failed"
#                 file_result["error"] = f"Unsupported file type: {file.content_type}"
#                 failed += 1
#                 results.append(file_result)
#                 continue

#             file_bytes = await file.read()

#             # Run full pipeline
#             pipeline_result = run_full_pipeline(
#                 file_bytes=file_bytes,
#                 content_type=file.content_type,
#                 user_id=current_user.id,
#                 db=db
#             )

#             if not pipeline_result["success"]:
#                 file_result["status"] = "failed"
#                 file_result["error"] = pipeline_result["error"]
#                 failed += 1
#                 results.append(file_result)
#                 continue

#             extracted_data = pipeline_result["extracted_data"]
#             classification = pipeline_result["classification"]
#             fraud_result = pipeline_result["fraud_result"]
#             ocr_result = pipeline_result["ocr_result"]
#             expense_status = pipeline_result["expense_status"]

#             # Save to database
#             new_expense = build_expense_object(
#                 user_id=current_user.id,
#                 expense_status=expense_status,
#                 extracted_data=extracted_data,
#                 classification=classification,
#                 fraud_result=fraud_result,
#                 ocr_result=ocr_result
#             )

#             db.add(new_expense)
#             db.commit()
#             db.refresh(new_expense)

#             # Track counts
#             if expense_status == "approved":
#                 successful += 1
#             else:
#                 pending += 1

#             file_result["status"] = "success"
#             file_result["expense_id"] = new_expense.id
#             file_result["expense_status"] = expense_status
#             file_result["vendor_name"] = extracted_data.get("vendor_name")
#             file_result["total_amount"] = extracted_data.get("total_amount")
#             file_result["category"] = classification.get("primary_category")
#             file_result["fraud_risk_score"] = fraud_result["fraud_risk_score"]

#         except Exception as e:
#             file_result["status"] = "failed"
#             file_result["error"] = str(e)
#             failed += 1

#         results.append(file_result)

#     return {
#         "status": "success",
#         "total_files": len(files),
#         "successful": successful,
#         "pending_verification": pending,
#         "failed": failed,
#         "results": results
#     }


# # ─────────────────────────────────────────────────────────
# # GET PENDING VERIFICATION EXPENSES
# # ─────────────────────────────────────────────────────────

# @router.get("/pending")
# def get_pending_expenses(
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Returns all expenses with status = pending_verification.
#     These are suspicious bills awaiting admin review.
#     They are NOT included in expense totals or dashboard.
#     """
#     expenses = db.query(Expense).filter(
#         Expense.user_id == current_user.id,
#         Expense.status == "pending_verification"
#     ).order_by(Expense.created_at.desc()).all()

#     return {
#         "status": "success",
#         "count": len(expenses),
#         "expenses": [
#             {
#                 "id": e.id,
#                 "vendor_name": e.vendor_name,
#                 "total_amount": e.total_amount,
#                 "primary_category": e.primary_category,
#                 "transaction_date": e.transaction_date,
#                 "fraud_risk_score": e.fraud_risk_score,
#                 "fraud_flags": e.fraud_flags,
#                 "confidence_score": e.confidence_score,
#                 "status": e.status,
#                 "created_at": str(e.created_at)
#             }
#             for e in expenses
#         ]
#     }


# # ─────────────────────────────────────────────────────────
# # DASHBOARD SUMMARY
# # ─────────────────────────────────────────────────────────

# @router.get("/summary")
# def get_expense_summary(
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Returns dashboard metrics.
#     ONLY counts approved expenses in totals.
#     Pending and rejected expenses are excluded from all calculations.
#     """

#     approved_expenses = db.query(Expense).filter(
#         Expense.user_id == current_user.id,
#         Expense.status == "approved"
#     ).all()

#     pending_count = db.query(Expense).filter(
#         Expense.user_id == current_user.id,
#         Expense.status == "pending_verification"
#     ).count()

#     rejected_count = db.query(Expense).filter(
#         Expense.user_id == current_user.id,
#         Expense.status == "rejected"
#     ).count()

#     if not approved_expenses:
#         return {
#             "status": "success",
#             "total_spend": 0,
#             "transaction_count": 0,
#             "pending_count": pending_count,
#             "rejected_count": rejected_count,
#             "avg_transaction": 0,
#             "category_breakdown": {},
#             "payment_method_breakdown": {}
#         }

#     total_spend = sum(
#         e.total_amount for e in approved_expenses if e.total_amount
#     )
#     avg_transaction = total_spend / len(approved_expenses)

#     # Spend by category — approved only
#     category_breakdown = {}
#     for e in approved_expenses:
#         if e.primary_category and e.total_amount:
#             cat = e.primary_category
#             category_breakdown[cat] = (
#                 category_breakdown.get(cat, 0) + e.total_amount
#             )

#     # Payment method distribution — approved only
#     payment_breakdown = {}
#     for e in approved_expenses:
#         if e.payment_method:
#             method = e.payment_method
#             payment_breakdown[method] = payment_breakdown.get(method, 0) + 1

#     return {
#         "status": "success",
#         "total_spend": round(total_spend, 2),
#         "transaction_count": len(approved_expenses),
#         "pending_count": pending_count,
#         "rejected_count": rejected_count,
#         "avg_transaction": round(avg_transaction, 2),
#         "category_breakdown": category_breakdown,
#         "payment_method_breakdown": payment_breakdown
#     }


# # ─────────────────────────────────────────────────────────
# # LIST ALL EXPENSES WITH FILTERS
# # ─────────────────────────────────────────────────────────

# @router.get("/")
# def get_all_expenses(
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user),
#     vendor_name: str = None,
#     category: str = None,
#     start_date: str = None,
#     end_date: str = None,
#     min_amount: float = None,
#     max_amount: float = None,
#     gstin: str = None,
#     requires_review: bool = None,
#     status: str = None
# ):
#     """
#     Returns expenses for the logged in user.
#     Default: only approved expenses shown.
#     Pass status=pending_verification or status=rejected to see others.

#     Filter options:
#     - vendor_name: partial match search
#     - category: Food & Dining, Travel & Transport, etc.
#     - start_date / end_date: YYYY-MM-DD format
#     - min_amount / max_amount: numeric
#     - gstin: GST number
#     - status: approved / pending_verification / rejected
#     """

#     query = db.query(Expense).filter(
#         Expense.user_id == current_user.id
#     )

#     # Default to approved only
#     if status:
#         query = query.filter(Expense.status == status)
#     else:
#         query = query.filter(Expense.status == "approved")

#     if vendor_name:
#         query = query.filter(
#             Expense.vendor_name.ilike(f"%{vendor_name}%")
#         )

#     if category:
#         query = query.filter(
#             Expense.primary_category.ilike(f"%{category}%")
#         )

#     if start_date:
#         query = query.filter(Expense.transaction_date >= start_date)

#     if end_date:
#         query = query.filter(Expense.transaction_date <= end_date)

#     if min_amount:
#         query = query.filter(Expense.total_amount >= min_amount)

#     if max_amount:
#         query = query.filter(Expense.total_amount <= max_amount)

#     if requires_review is not None:
#         query = query.filter(
#             Expense.requires_manual_review == requires_review
#         )

#     query = query.order_by(Expense.created_at.desc())
#     expenses = query.all()

#     total_spend = sum(e.total_amount for e in expenses if e.total_amount)
#     flagged_count = sum(1 for e in expenses if e.requires_manual_review)

#     return {
#         "status": "success",
#         "count": len(expenses),
#         "total_spend": round(total_spend, 2),
#         "flagged_count": flagged_count,
#         "filters_applied": {
#             "vendor_name": vendor_name,
#             "category": category,
#             "start_date": start_date,
#             "end_date": end_date,
#             "min_amount": min_amount,
#             "max_amount": max_amount,
#             "gstin": gstin,
#             "requires_review": requires_review,
#             "status": status or "approved"
#         },
#         "expenses": [
#             {
#                 "id": e.id,
#                 "vendor_name": e.vendor_name,
#                 "total_amount": e.total_amount,
#                 "primary_category": e.primary_category,
#                 "subcategory": e.subcategory,
#                 "transaction_date": e.transaction_date,
#                 "payment_method": e.payment_method,
#                 "currency_code": e.currency_code,
#                 "fraud_risk_score": e.fraud_risk_score,
#                 "requires_manual_review": e.requires_manual_review,
#                 "confidence_score": e.confidence_score,
#                 "receipt_number": e.receipt_number,
#                 "status": e.status,
#                 "created_at": str(e.created_at)
#             }
#             for e in expenses
#         ]
#     }


# # ─────────────────────────────────────────────────────────
# # APPROVE A PENDING EXPENSE
# # ─────────────────────────────────────────────────────────

# @router.put("/{expense_id}/approve")
# def approve_expense(
#     expense_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Approves a pending expense.
#     Moves it from Pending Verification to Approved.
#     It will now appear in expense totals and dashboard.
#     """
#     expense = db.query(Expense).filter(
#         Expense.id == expense_id,
#         Expense.user_id == current_user.id
#     ).first()

#     if not expense:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Expense {expense_id} not found"
#         )

#     if expense.status == "approved":
#         raise HTTPException(
#             status_code=400,
#             detail="Expense is already approved"
#         )

#     expense.status = "approved"
#     db.commit()
#     db.refresh(expense)

#     return {
#         "status": "success",
#         "message": f"Expense {expense_id} approved and added to your expense list",
#         "expense_id": expense_id,
#         "new_status": "approved"
#     }


# # ─────────────────────────────────────────────────────────
# # REJECT A PENDING EXPENSE
# # ─────────────────────────────────────────────────────────

# @router.put("/{expense_id}/reject")
# def reject_expense(
#     expense_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Rejects a pending expense.
#     Moves it to Rejected status.
#     It will be archived and excluded from all expense calculations.
#     """
#     expense = db.query(Expense).filter(
#         Expense.id == expense_id,
#         Expense.user_id == current_user.id
#     ).first()

#     if not expense:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Expense {expense_id} not found"
#         )

#     if expense.status == "rejected":
#         raise HTTPException(
#             status_code=400,
#             detail="Expense is already rejected"
#         )

#     expense.status = "rejected"
#     db.commit()
#     db.refresh(expense)

#     return {
#         "status": "success",
#         "message": f"Expense {expense_id} rejected and archived",
#         "expense_id": expense_id,
#         "new_status": "rejected"
#     }


# # ─────────────────────────────────────────────────────────
# # GET SINGLE EXPENSE BY ID
# # ─────────────────────────────────────────────────────────

# @router.get("/{expense_id}")
# def get_expense_by_id(
#     expense_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Returns full details of a single expense by ID.
#     Only returns the expense if it belongs to the current user.
#     """
#     expense = db.query(Expense).filter(
#         Expense.id == expense_id,
#         Expense.user_id == current_user.id
#     ).first()

#     if not expense:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Expense with id {expense_id} not found"
#         )

#     return {
#         "status": "success",
#         "expense": {
#             "id": expense.id,
#             "vendor_name": expense.vendor_name,
#             "vendor_category": expense.vendor_category,
#             "total_amount": expense.total_amount,
#             "subtotal": expense.subtotal,
#             "tax_amount": expense.tax_amount,
#             "tax_type": expense.tax_type,
#             "currency_code": expense.currency_code,
#             "payment_method": expense.payment_method,
#             "primary_category": expense.primary_category,
#             "subcategory": expense.subcategory,
#             "classification_confidence": expense.classification_confidence,
#             "transaction_date": expense.transaction_date,
#             "receipt_number": expense.receipt_number,
#             "fraud_risk_score": expense.fraud_risk_score,
#             "fraud_flags": expense.fraud_flags,
#             "requires_manual_review": expense.requires_manual_review,
#             "confidence_score": expense.confidence_score,
#             "extracted_data": expense.extracted_data,
#             "status": expense.status,
#             "created_at": str(expense.created_at)
#         }
#     }


# # ─────────────────────────────────────────────────────────
# # DELETE AN EXPENSE
# # ─────────────────────────────────────────────────────────

# @router.delete("/{expense_id}")
# def delete_expense(
#     expense_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user)
# ):
#     """
#     Permanently deletes an expense.
#     Only allowed if the expense belongs to the current user.
#     """
#     expense = db.query(Expense).filter(
#         Expense.id == expense_id,
#         Expense.user_id == current_user.id
#     ).first()

#     if not expense:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Expense with id {expense_id} not found"
#         )

#     db.delete(expense)
#     db.commit()

#     return {
#         "status": "success",
#         "message": f"Expense {expense_id} deleted successfully"
#     }

# expense_router.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.ocr_service import extract_text_from_image, extract_text_from_pdf
from services.ai_service import extract_expense_data, classify_expense
from services.fraud_service import check_fraud
from models.expense import Expense
from dependencies import get_current_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/scan-receipt")
async def scan_receipt(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    image_types = ["image/jpeg", "image/png", "image/jpg", "image/webp", "image/tiff", "image/bmp"]
    pdf_types = ["application/pdf"]
    allowed_types = image_types + pdf_types

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not supported.")

    file_bytes = await file.read()

    if file.content_type in pdf_types:
        ocr_result = extract_text_from_pdf(file_bytes)
    else:
        ocr_result = extract_text_from_image(file_bytes)

    if ocr_result.get("error"):
        raise HTTPException(status_code=422, detail=f"OCR failed: {ocr_result['error']}")

    if ocr_result["word_count"] < 3:
        raise HTTPException(status_code=422, detail="Could not extract enough text. Please upload a clearer image or PDF.")

    ai_result = extract_expense_data(ocr_result["cleaned_text"])
    if ai_result["status"] == "error":
        raise HTTPException(status_code=500, detail=f"AI extraction failed: {ai_result['error']}")

    extracted_data = ai_result["data"]

    # Validate this is actually a receipt
    if not extracted_data.get("total_amount") and not extracted_data.get("vendor_name"):
        raise HTTPException(status_code=422, detail="This file does not appear to be a receipt or bill. No financial data found.")

    classification_result = classify_expense(
        vendor_name=extracted_data.get("vendor_name", "Unknown"),
        line_items=extracted_data.get("line_items", []),
        vendor_hint=extracted_data.get("vendor_category_hint", None)
    )
    classification = classification_result.get("data", {})

    fraud_result = check_fraud(
        extracted_data=extracted_data,
        classification=classification,
        ocr_confidence=ocr_result["confidence_score"],
        user_id=current_user.id,
        db=db
    )

    new_expense = Expense(
        user_id=current_user.id,
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

    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    return {
        "status": "success",
        "expense_id": new_expense.id,
        "filename": file.filename,
        "file_type": file.content_type,
        "ocr": {
            "confidence_score": ocr_result["confidence_score"],
            "word_count": ocr_result["word_count"],
            "source": ocr_result.get("source", "image"),
            "pages": ocr_result.get("pages", 1)
        },
        "extracted_data": extracted_data,
        "classification": classification,
        "fraud_analysis": fraud_result
    }


@router.get("/summary")
def get_expense_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    expenses = db.query(Expense).filter(Expense.user_id == current_user.id).all()

    if not expenses:
        return {
            "status": "success",
            "total_spend": 0,
            "transaction_count": 0,
            "flagged_count": 0,
            "avg_transaction": 0,
            "category_breakdown": {},
            "payment_method_breakdown": {}
        }

    total_spend = sum(e.total_amount for e in expenses if e.total_amount)
    flagged_count = sum(1 for e in expenses if e.requires_manual_review)
    avg_transaction = total_spend / len(expenses) if expenses else 0

    category_breakdown = {}
    for e in expenses:
        if e.primary_category and e.total_amount:
            category_breakdown[e.primary_category] = category_breakdown.get(e.primary_category, 0) + e.total_amount

    payment_breakdown = {}
    for e in expenses:
        if e.payment_method:
            payment_breakdown[e.payment_method] = payment_breakdown.get(e.payment_method, 0) + 1

    return {
        "status": "success",
        "total_spend": round(total_spend, 2),
        "transaction_count": len(expenses),
        "flagged_count": flagged_count,
        "avg_transaction": round(avg_transaction, 2),
        "category_breakdown": category_breakdown,
        "payment_method_breakdown": payment_breakdown
    }


@router.get("/")
def get_all_expenses(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    vendor_name: str = None,
    category: str = None,
    start_date: str = None,
    end_date: str = None,
    min_amount: float = None,
    max_amount: float = None,
    gstin: str = None,
    requires_review: bool = None
):
    query = db.query(Expense).filter(Expense.user_id == current_user.id)

    if vendor_name:
        query = query.filter(Expense.vendor_name.ilike(f"%{vendor_name}%"))
    if category:
        query = query.filter(Expense.primary_category.ilike(f"%{category}%"))
    if start_date:
        query = query.filter(Expense.transaction_date >= start_date)
    if end_date:
        query = query.filter(Expense.transaction_date <= end_date)
    if min_amount:
        query = query.filter(Expense.total_amount >= min_amount)
    if max_amount:
        query = query.filter(Expense.total_amount <= max_amount)
    if requires_review is not None:
        query = query.filter(Expense.requires_manual_review == requires_review)

    query = query.order_by(Expense.created_at.desc())
    expenses = query.all()

    total_spend = sum(e.total_amount for e in expenses if e.total_amount)
    flagged_count = sum(1 for e in expenses if e.requires_manual_review)

    return {
        "status": "success",
        "count": len(expenses),
        "total_spend": round(total_spend, 2),
        "flagged_count": flagged_count,
        "filters_applied": {
            "vendor_name": vendor_name,
            "category": category,
            "start_date": start_date,
            "end_date": end_date,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "gstin": gstin,
            "requires_review": requires_review
        },
        "expenses": [
            {
                "id": e.id,
                "vendor_name": e.vendor_name,
                "total_amount": e.total_amount,
                "primary_category": e.primary_category,
                "subcategory": e.subcategory,
                "transaction_date": e.transaction_date,
                "payment_method": e.payment_method,
                "currency_code": e.currency_code,
                "fraud_risk_score": e.fraud_risk_score,
                "requires_manual_review": e.requires_manual_review,
                "confidence_score": e.confidence_score,
                "receipt_number": e.receipt_number,
                "created_at": str(e.created_at)
            }
            for e in expenses
        ]
    }


@router.get("/{expense_id}")
def get_expense_by_id(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found")

    return {
        "status": "success",
        "expense": {
            "id": expense.id,
            "vendor_name": expense.vendor_name,
            "vendor_category": expense.vendor_category,
            "total_amount": expense.total_amount,
            "subtotal": expense.subtotal,
            "tax_amount": expense.tax_amount,
            "tax_type": expense.tax_type,
            "currency_code": expense.currency_code,
            "payment_method": expense.payment_method,
            "primary_category": expense.primary_category,
            "subcategory": expense.subcategory,
            "classification_confidence": expense.classification_confidence,
            "transaction_date": expense.transaction_date,
            "receipt_number": expense.receipt_number,
            "fraud_risk_score": expense.fraud_risk_score,
            "fraud_flags": expense.fraud_flags,
            "requires_manual_review": expense.requires_manual_review,
            "confidence_score": expense.confidence_score,
            "extracted_data": expense.extracted_data,
            "created_at": str(expense.created_at)
        }
    }


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    expense = db.query(Expense).filter(
        Expense.id == expense_id,
        Expense.user_id == current_user.id
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found")

    db.delete(expense)
    db.commit()

    return {"status": "success", "message": f"Expense {expense_id} deleted successfully"}