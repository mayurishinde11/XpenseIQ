"""
XpenseIQ — Expense Router
=========================
Key improvements over v1:
  • scan-bulk  → true async concurrent processing via asyncio.gather
  • Multi-page PDF → each page is extracted and processed as a separate bill
  • DB writes are batched after all pipelines finish (one commit per bulk job)
  • Every per-file error is isolated; a bad file never aborts the batch
  • scan-receipt remains unchanged in behaviour (uses the same shared helpers)
"""

import asyncio
import io
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.expense import Expense
from routers.auth_router import get_current_user
from services.ai_service import classify_expense, extract_expense_data
from services.fraud_service import check_fraud
from services.ocr_service import (
    extract_text_from_image,
    extract_text_from_pdf,
    validate_image_file,
)

# ── pypdf is only needed for page-splitting; fail gracefully if absent ──────
try:
    from pypdf import PdfReader, PdfWriter          # pypdf ≥ 3.x
    PYPDF_AVAILABLE = True
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter     # legacy fallback
        PYPDF_AVAILABLE = True
    except ImportError:
        PYPDF_AVAILABLE = False

router = APIRouter(prefix="/expenses", tags=["Expenses"])

ALLOWED_TYPES = [
    "image/jpeg", "image/png", "image/jpg",
    "image/webp", "image/tiff", "image/bmp",
    "application/pdf",
]
PDF_TYPE  = "application/pdf"
MAX_BULK  = 20          # raised from 10; each multi-page PDF still counts as 1
MAX_PAGES = 30          # safety cap: ignore pages beyond this per PDF


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def split_pdf_pages(pdf_bytes: bytes) -> list[bytes]:
    """
    Split a PDF into individual single-page PDFs.
    Returns a list of bytes objects (one per page).
    Falls back to returning the whole PDF as one item if pypdf is unavailable.
    """
    if not PYPDF_AVAILABLE:
        return [pdf_bytes]

    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages  = []
    for i, page in enumerate(reader.pages):
        if i >= MAX_PAGES:
            break
        writer = PdfWriter()
        writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        pages.append(buf.getvalue())
    return pages or [pdf_bytes]


def build_expense_object(
    user_id:        int,
    expense_status: str,
    extracted_data: dict,
    classification: dict,
    fraud_result:   dict,
    ocr_result:     dict,
) -> Expense:
    """Construct an Expense ORM object from pipeline outputs."""
    return Expense(
        user_id=user_id,
        status=expense_status,
        # Vendor
        vendor_name=extracted_data.get("vendor_name"),
        vendor_category=extracted_data.get("vendor_category_hint"),
        # Financials
        total_amount=extracted_data.get("total_amount"),
        subtotal=extracted_data.get("subtotal"),
        tax_amount=extracted_data.get("tax_amount"),
        tax_type=extracted_data.get("tax_type"),
        currency_code=extracted_data.get("currency_code", "INR"),
        # Payment
        payment_method=extracted_data.get("payment_method"),
        # Classification
        primary_category=classification.get("primary_category"),
        subcategory=classification.get("subcategory"),
        classification_confidence=classification.get("classification_confidence"),
        # Fraud
        fraud_risk_score=fraud_result["fraud_risk_score"],
        is_duplicate=fraud_result["is_duplicate"],
        requires_manual_review=fraud_result["requires_manual_review"],
        fraud_flags=fraud_result["fraud_flags"],
        # OCR
        raw_ocr_text=ocr_result["cleaned_text"],
        confidence_score=ocr_result["confidence_score"],
        # Receipt
        receipt_number=extracted_data.get("receipt_number"),
        extracted_data=extracted_data,
        transaction_date=extracted_data.get("transaction_date"),
    )


def run_full_pipeline(
    file_bytes:   bytes,
    content_type: str,
    user_id:      int,
    db:           Session,
) -> dict:
    """
    Synchronous pipeline: validate → OCR → AI extract → classify → fraud check.
    Returns a result dict with success=True/False.
    """
    # Stage 1 — Validation
    validation = validate_image_file(file_bytes, content_type)
    if not validation["is_valid"]:
        return {"success": False, "error": validation["reason"]}

    # Stage 2 — OCR
    if content_type == PDF_TYPE:
        ocr_result = extract_text_from_pdf(file_bytes)
    else:
        ocr_result = extract_text_from_image(file_bytes)

    if ocr_result.get("error"):
        return {"success": False, "error": f"OCR failed: {ocr_result['error']}"}
    if ocr_result["word_count"] < 3:
        return {
            "success": False,
            "error": "Could not extract enough text. Please upload a clearer image.",
        }

    # Stage 3 — AI Extraction
    ai_result = extract_expense_data(ocr_result["cleaned_text"])
    if ai_result["status"] == "error":
        return {"success": False, "error": f"AI extraction failed: {ai_result['error']}"}

    extracted_data = ai_result["data"]

    # Stage 4 — Receipt Validity
    total_amount = extracted_data.get("total_amount")
    vendor_name  = extracted_data.get("vendor_name")

    if not total_amount and not vendor_name:
        return {
            "success": False,
            "error": "File does not appear to be a receipt/bill. No financial data found.",
        }
    if not total_amount:
        return {
            "success": False,
            "error": "Could not extract total amount. Please upload a clearer receipt.",
        }

    # Stage 5 — AI Classification
    classification_result = classify_expense(
        vendor_name=vendor_name or "Unknown",
        line_items=extracted_data.get("line_items", []),
        vendor_hint=extracted_data.get("vendor_category_hint"),
    )
    classification = classification_result.get("data", {})

    # Stage 6 — Fraud Detection
    fraud_result = check_fraud(
        extracted_data=extracted_data,
        classification=classification,
        ocr_confidence=ocr_result["confidence_score"],
        user_id=user_id,
        db=db,
    )

    # Stage 7 — Status
    expense_status = (
        "pending_verification"
        if fraud_result["fraud_risk_score"] >= 0.5 or fraud_result["requires_manual_review"]
        else "approved"
    )

    return {
        "success":        True,
        "extracted_data": extracted_data,
        "classification": classification,
        "fraud_result":   fraud_result,
        "ocr_result":     ocr_result,
        "expense_status": expense_status,
    }


async def process_single_file(
    file_bytes:   bytes,
    content_type: str,
    filename:     str,
    user_id:      int,
    db:           Session,
    page_label:   Optional[str] = None,
) -> dict:
    """
    Async wrapper around run_full_pipeline for a single file/page.
    Returns a standardised result dict ready for bulk aggregation.
    """
    label = page_label or filename
    result = {
        "filename":         label,
        "original_file":    filename,
        "status":           None,
        "expense_id":       None,   # filled after DB commit
        "expense_status":   None,
        "error":            None,
        "vendor_name":      None,
        "total_amount":     None,
        "category":         None,
        "subcategory":      None,
        "fraud_risk_score": None,
    }

    try:
        # Open a fresh database session for the concurrent pipeline run
        # to ensure thread-safety across background thread pools.
        from database import SessionLocal
        with SessionLocal() as thread_db:
            # Run blocking pipeline in a thread pool so we don't block the event loop
            pipeline = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: run_full_pipeline(file_bytes, content_type, user_id, thread_db),
            )

        if not pipeline["success"]:
            result["status"] = "failed"
            result["error"]  = pipeline["error"]
            return result

        result["_pipeline"] = pipeline   # stash for caller to use
        result["status"]    = "processed"

    except Exception as exc:
        result["status"] = "failed"
        result["error"]  = str(exc)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLE RECEIPT SCAN
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/scan-receipt")
async def scan_receipt(
    file:         UploadFile = File(...),
    db:           Session    = Depends(get_db),
    current_user             = Depends(get_current_user),
):
    """
    Scan a single receipt (image or PDF).

    Pipeline:
    1. Validate file
    2. OCR
    3. AI extraction (vendor, amount, date, GSTIN …)
    4. Receipt validity check
    5. AI classification
    6. Fraud detection
    7. Set status → save to DB
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="File type not supported. Accepted: JPG, PNG, WEBP, TIFF, BMP, PDF.",
        )

    file_bytes = await file.read()

    pipeline = run_full_pipeline(
        file_bytes=file_bytes,
        content_type=file.content_type,
        user_id=current_user.id,
        db=db,
    )

    if not pipeline["success"]:
        raise HTTPException(status_code=422, detail=pipeline["error"])

    extracted_data  = pipeline["extracted_data"]
    classification  = pipeline["classification"]
    fraud_result    = pipeline["fraud_result"]
    ocr_result      = pipeline["ocr_result"]
    expense_status  = pipeline["expense_status"]

    new_expense = build_expense_object(
        user_id=current_user.id,
        expense_status=expense_status,
        extracted_data=extracted_data,
        classification=classification,
        fraud_result=fraud_result,
        ocr_result=ocr_result,
    )

    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    return {
        "status":         "success",
        "expense_id":     new_expense.id,
        "expense_status": expense_status,
        "filename":       file.filename,
        "file_type":      file.content_type,
        "ocr": {
            "confidence_score": ocr_result["confidence_score"],
            "word_count":       ocr_result["word_count"],
            "source":           ocr_result.get("source", "image"),
            "pages":            ocr_result.get("pages", 1),
        },
        "extracted_data":  extracted_data,
        "classification":  classification,
        "fraud_analysis":  fraud_result,
        "message": (
            "Receipt scanned and approved successfully."
            if expense_status == "approved"
            else "Receipt flagged for verification. Check the Pending Verification tab."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# BULK RECEIPT SCAN  ← main fix
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/scan-bulk")
async def scan_bulk_receipts(
    files:        list[UploadFile] = File(...),
    db:           Session          = Depends(get_db),
    current_user                   = Depends(get_current_user),
):
    """
    Scan multiple receipts (images and/or PDFs) in one request.

    Key behaviours
    ──────────────
    • Up to 20 files per request (each PDF can contain many pages).
    • Multi-page PDFs are split into individual pages; each page is
      analysed as a separate bill and saved as its own expense record.
    • All files/pages are processed concurrently (asyncio.gather) so
      a 10-file upload is not 10× slower than a single upload.
    • Database rows are inserted in a single batch commit after all
      pipelines complete, reducing round-trips.
    • A failure on one file/page never aborts the rest of the batch.

    Response summary fields
    ───────────────────────
    total_files          – number of UploadFile objects received
    total_pages          – total units processed (pages across all PDFs + images)
    successful           – saved with status=approved
    pending_verification – saved with status=pending_verification
    failed               – could not be processed (per-item error included)
    results              – per-page detail list
    """

    if len(files) > MAX_BULK:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_BULK} files per bulk upload. Split into smaller batches.",
        )

    # ── Step 1: Read all files and expand multi-page PDFs ────────────────────
    work_items: list[dict] = []   # {bytes, content_type, filename, page_label}

    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            # Record bad type immediately as a failed result
            work_items.append({
                "bytes":        None,
                "content_type": file.content_type,
                "filename":     file.filename,
                "page_label":   file.filename,
                "prefailed":    f"Unsupported file type: {file.content_type}",
            })
            continue

        raw = await file.read()

        if file.content_type == PDF_TYPE:
            pages = split_pdf_pages(raw)
            if len(pages) == 1:
                # Single-page PDF or pypdf unavailable — treat as one unit
                work_items.append({
                    "bytes":        pages[0],
                    "content_type": PDF_TYPE,
                    "filename":     file.filename,
                    "page_label":   file.filename,
                    "prefailed":    None,
                })
            else:
                for idx, page_bytes in enumerate(pages, start=1):
                    work_items.append({
                        "bytes":        page_bytes,
                        "content_type": PDF_TYPE,
                        "filename":     file.filename,
                        "page_label":   f"{file.filename} — page {idx}",
                        "prefailed":    None,
                    })
        else:
            work_items.append({
                "bytes":        raw,
                "content_type": file.content_type,
                "filename":     file.filename,
                "page_label":   file.filename,
                "prefailed":    None,
            })

    # ── Step 2: Launch all pipelines concurrently ────────────────────────────
    async def _process(item: dict) -> dict:
        if item.get("prefailed"):
            return {
                "filename":         item["page_label"],
                "original_file":    item["filename"],
                "status":           "failed",
                "expense_id":       None,
                "expense_status":   None,
                "error":            item["prefailed"],
                "vendor_name":      None,
                "total_amount":     None,
                "category":         None,
                "subcategory":      None,
                "fraud_risk_score": None,
            }
        return await process_single_file(
            file_bytes=item["bytes"],
            content_type=item["content_type"],
            filename=item["filename"],
            user_id=current_user.id,
            db=db,
            page_label=item["page_label"],
        )

    raw_results = await asyncio.gather(*[_process(item) for item in work_items])

    # ── Step 3: Batch DB insert for successful results ───────────────────────
    new_expenses: list[Expense] = []
    success_indices: list[int]  = []

    for i, res in enumerate(raw_results):
        if res["status"] == "processed" and "_pipeline" in res:
            pipeline = res.pop("_pipeline")
            exp = build_expense_object(
                user_id=current_user.id,
                expense_status=pipeline["expense_status"],
                extracted_data=pipeline["extracted_data"],
                classification=pipeline["classification"],
                fraud_result=pipeline["fraud_result"],
                ocr_result=pipeline["ocr_result"],
            )
            new_expenses.append(exp)
            success_indices.append(i)

            # Pre-fill result fields (expense_id set after flush)
            res["expense_status"]   = pipeline["expense_status"]
            res["vendor_name"]      = pipeline["extracted_data"].get("vendor_name")
            res["total_amount"]     = pipeline["extracted_data"].get("total_amount")
            res["category"]         = pipeline["classification"].get("primary_category")
            res["subcategory"]      = pipeline["classification"].get("subcategory")
            res["fraud_risk_score"] = pipeline["fraud_result"]["fraud_risk_score"]

    if new_expenses:
        db.add_all(new_expenses)
        db.flush()          # assigns IDs without a full commit
        db.commit()

        for i, exp in zip(success_indices, new_expenses):
            db.refresh(exp)
            raw_results[i]["expense_id"] = exp.id
            raw_results[i]["status"]     = "success"

    # ── Step 4: Compute summary counters ────────────────────────────────────
    successful = sum(1 for r in raw_results if r["status"] == "success" and r["expense_status"] == "approved")
    pending    = sum(1 for r in raw_results if r["status"] == "success" and r["expense_status"] == "pending_verification")
    failed     = sum(1 for r in raw_results if r["status"] == "failed")

    return {
        "status":               "success",
        "total_files":          len(files),
        "total_pages":          len(work_items),
        "successful":           successful,
        "pending_verification": pending,
        "failed":               failed,
        "results":              list(raw_results),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PENDING VERIFICATION LIST
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/insights")
def get_ai_insights(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Returns 3 AI-generated insights about spending patterns.
    Based on approved expenses only.
    """
    from services.ai_service import generate_insights

    expenses = db.query(Expense).filter(
        Expense.user_id == current_user.id,
        Expense.status == "approved"
    ).order_by(Expense.created_at.desc()).limit(20).all()

    expense_list = [
        {
            "vendor_name": e.vendor_name,
            "total_amount": e.total_amount,
            "primary_category": e.primary_category,
            "transaction_date": e.transaction_date
        }
        for e in expenses
    ]

    result = generate_insights(expense_list)

    return {
        "status": "success",
        "insights": result.get("data", {}).get("insights", [])
    }


@router.get("/pending")
def get_pending_expenses(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """Return all expenses awaiting manual review."""
    expenses = (
        db.query(Expense)
        .filter(
            Expense.user_id == current_user.id,
            Expense.status  == "pending_verification",
        )
        .order_by(Expense.created_at.desc())
        .all()
    )

    return {
        "status":   "success",
        "count":    len(expenses),
        "expenses": [
            {
                "id":               e.id,
                "vendor_name":      e.vendor_name,
                "total_amount":     e.total_amount,
                "primary_category": e.primary_category,
                "transaction_date": e.transaction_date,
                "fraud_risk_score": e.fraud_risk_score,
                "fraud_flags":      e.fraud_flags,
                "confidence_score": e.confidence_score,
                "status":           e.status,
                "created_at":       str(e.created_at),
            }
            for e in expenses
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/summary")
def get_expense_summary(
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """
    Dashboard metrics.
    Only approved expenses are included in spend totals.
    """
    approved = (
        db.query(Expense)
        .filter(Expense.user_id == current_user.id, Expense.status == "approved")
        .all()
    )
    pending_count  = db.query(Expense).filter(Expense.user_id == current_user.id, Expense.status == "pending_verification").count()
    rejected_count = db.query(Expense).filter(Expense.user_id == current_user.id, Expense.status == "rejected").count()

    if not approved:
        return {
            "status":                   "success",
            "total_spend":              0,
            "transaction_count":        0,
            "pending_count":            pending_count,
            "rejected_count":           rejected_count,
            "avg_transaction":          0,
            "category_breakdown":       {},
            "payment_method_breakdown": {},
        }

    total_spend = sum(e.total_amount for e in approved if e.total_amount)
    avg_tx      = total_spend / len(approved)

    category_breakdown: dict[str, float] = {}
    for e in approved:
        if e.primary_category and e.total_amount:
            category_breakdown[e.primary_category] = (
                category_breakdown.get(e.primary_category, 0) + e.total_amount
            )

    payment_breakdown: dict[str, int] = {}
    for e in approved:
        if e.payment_method:
            payment_breakdown[e.payment_method] = payment_breakdown.get(e.payment_method, 0) + 1

    return {
        "status":                   "success",
        "total_spend":              round(total_spend, 2),
        "transaction_count":        len(approved),
        "pending_count":            pending_count,
        "rejected_count":           rejected_count,
        "avg_transaction":          round(avg_tx, 2),
        "category_breakdown":       category_breakdown,
        "payment_method_breakdown": payment_breakdown,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# LIST ALL EXPENSES WITH FILTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
def get_all_expenses(
    db:              Session       = Depends(get_db),
    current_user                   = Depends(get_current_user),
    vendor_name:     str           = None,
    category:        str           = None,
    start_date:      str           = None,
    end_date:        str           = None,
    min_amount:      float         = None,
    max_amount:      float         = None,
    gstin:           str           = None,
    requires_review: bool          = None,
    status:          str           = None,
):
    """
    List expenses for the current user with optional filters.
    Defaults to approved expenses only.
    """
    query = db.query(Expense).filter(Expense.user_id == current_user.id)
    query = query.filter(Expense.status == (status or "approved"))

    if vendor_name:
        query = query.filter(Expense.vendor_name.ilike(f"%{vendor_name}%"))
    if category:
        query = query.filter(Expense.primary_category.ilike(f"%{category}%"))
    if start_date:
        query = query.filter(Expense.transaction_date >= start_date)
    if end_date:
        query = query.filter(Expense.transaction_date <= end_date)
    if min_amount is not None:
        query = query.filter(Expense.total_amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Expense.total_amount <= max_amount)
    if requires_review is not None:
        query = query.filter(Expense.requires_manual_review == requires_review)

    query    = query.order_by(Expense.created_at.desc())
    expenses = query.all()

    total_spend   = sum(e.total_amount for e in expenses if e.total_amount)
    flagged_count = sum(1 for e in expenses if e.requires_manual_review)

    return {
        "status":       "success",
        "count":        len(expenses),
        "total_spend":  round(total_spend, 2),
        "flagged_count": flagged_count,
        "filters_applied": {
            "vendor_name":    vendor_name,
            "category":       category,
            "start_date":     start_date,
            "end_date":       end_date,
            "min_amount":     min_amount,
            "max_amount":     max_amount,
            "gstin":          gstin,
            "requires_review": requires_review,
            "status":         status or "approved",
        },
        "expenses": [
            {
                "id":                    e.id,
                "vendor_name":           e.vendor_name,
                "total_amount":          e.total_amount,
                "primary_category":      e.primary_category,
                "subcategory":           e.subcategory,
                "transaction_date":      e.transaction_date,
                "payment_method":        e.payment_method,
                "currency_code":         e.currency_code,
                "fraud_risk_score":      e.fraud_risk_score,
                "requires_manual_review": e.requires_manual_review,
                "confidence_score":      e.confidence_score,
                "receipt_number":        e.receipt_number,
                "status":                e.status,
                "created_at":            str(e.created_at),
            }
            for e in expenses
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# APPROVE / REJECT
# ═══════════════════════════════════════════════════════════════════════════════

@router.put("/{expense_id}/approve")
def approve_expense(
    expense_id:   int,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """Move a pending expense to approved."""
    expense = db.query(Expense).filter(
        Expense.id      == expense_id,
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found.")
    if expense.status == "approved":
        raise HTTPException(status_code=400, detail="Expense is already approved.")

    expense.status = "approved"
    db.commit()
    db.refresh(expense)

    return {
        "status":     "success",
        "message":    f"Expense {expense_id} approved.",
        "expense_id": expense_id,
        "new_status": "approved",
    }


@router.put("/{expense_id}/reject")
def reject_expense(
    expense_id:   int,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    """Move an expense to rejected/archived."""
    expense = db.query(Expense).filter(
        Expense.id      == expense_id,
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found.")
    if expense.status == "rejected":
        raise HTTPException(status_code=400, detail="Expense is already rejected.")

    expense.status = "rejected"
    db.commit()
    db.refresh(expense)

    return {
        "status":     "success",
        "message":    f"Expense {expense_id} rejected and archived.",
        "expense_id": expense_id,
        "new_status": "rejected",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET SINGLE EXPENSE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{expense_id}")
def get_expense_by_id(
    expense_id:   int,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    expense = db.query(Expense).filter(
        Expense.id      == expense_id,
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found.")

    return {
        "status": "success",
        "expense": {
            "id":                       expense.id,
            "vendor_name":              expense.vendor_name,
            "vendor_category":          expense.vendor_category,
            "total_amount":             expense.total_amount,
            "subtotal":                 expense.subtotal,
            "tax_amount":               expense.tax_amount,
            "tax_type":                 expense.tax_type,
            "currency_code":            expense.currency_code,
            "payment_method":           expense.payment_method,
            "primary_category":         expense.primary_category,
            "subcategory":              expense.subcategory,
            "classification_confidence": expense.classification_confidence,
            "transaction_date":         expense.transaction_date,
            "receipt_number":           expense.receipt_number,
            "fraud_risk_score":         expense.fraud_risk_score,
            "fraud_flags":              expense.fraud_flags,
            "requires_manual_review":   expense.requires_manual_review,
            "confidence_score":         expense.confidence_score,
            "extracted_data":           expense.extracted_data,
            "status":                   expense.status,
            "created_at":               str(expense.created_at),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE EXPENSE
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete("/{expense_id}")
def delete_expense(
    expense_id:   int,
    db:           Session = Depends(get_db),
    current_user          = Depends(get_current_user),
):
    expense = db.query(Expense).filter(
        Expense.id      == expense_id,
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        raise HTTPException(status_code=404, detail=f"Expense {expense_id} not found.")

    db.delete(expense)
    db.commit()

    return {
        "status":  "success",
        "message": f"Expense {expense_id} deleted successfully.",
    }