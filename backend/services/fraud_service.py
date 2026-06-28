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

    total_amount     = extracted_data.get("total_amount", 0) or 0
    vendor_name      = extracted_data.get("vendor_name", "") or ""
    transaction_date = extracted_data.get("transaction_date", "") or ""
    receipt_number   = extracted_data.get("receipt_number", None)
    subtotal         = extracted_data.get("subtotal", 0) or 0
    tax_amount       = extracted_data.get("tax_amount", 0) or 0
    gstin            = extracted_data.get("gstin", None) or ""
    line_items       = extracted_data.get("line_items", []) or []
    discount         = extracted_data.get("discount_amount", 0) or 0
    extra_charges    = extracted_data.get("extra_charges", 0) or 0
    service_charge   = extracted_data.get("service_charge", 0) or 0

    # ── RULE 1 — Low OCR confidence ──────────────────────────────────────────
    if ocr_confidence < 0.60:
        fraud_flags.append("Low OCR confidence — receipt may be unclear or fake")
        fraud_risk_score += 0.25

    # ── RULE 2 — Suspiciously round amount ───────────────────────────────────
    if total_amount > 0 and total_amount % 1000 == 0:
        fraud_flags.append(f"Suspiciously round amount: ₹{total_amount}")
        fraud_risk_score += 0.20

    # ── RULE 3 — Missing receipt number ──────────────────────────────────────
    if not receipt_number:
        fraud_flags.append("Missing receipt number")
        fraud_risk_score += 0.10

    # ── RULE 4 — Weekend transaction for B2B vendor ───────────────────────────
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

    # ── RULE 5 — Duplicate detection ─────────────────────────────────────────
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

    # ── RULE 6 — High value transaction ──────────────────────────────────────
    if total_amount > 50000:
        fraud_flags.append(f"High value transaction: ₹{total_amount}")
        fraud_risk_score += 0.15

    # ── RULE 7 — Amount mismatch (includes discount, extra charges, service) ──
    if subtotal > 0 and tax_amount > 0:
        expected_total = round(
            subtotal - discount + extra_charges + service_charge + tax_amount, 2
        )
        # Also calculate from line items if available
        line_items_total = sum(
            item.get("total_price") or 0 for item in line_items
        ) if line_items else 0

        # Use line items total as subtotal if it's closer to actual total
        if line_items_total > 0 and abs(line_items_total - subtotal) > 2.0:
            expected_total = round(
                line_items_total - discount + extra_charges + service_charge + tax_amount, 2
            )

        if abs(expected_total - total_amount) > 2.0:
            fraud_flags.append(
                f"Amount mismatch: subtotal ({subtotal}) - discount ({discount}) "
                f"+ extra ({extra_charges}) + tax ({tax_amount}) "
                f"= {expected_total} but total shown as {total_amount}"
            )
            fraud_risk_score += 0.30

    # RULE 7B — Invalid GSTIN format + fake GSTIN detection
    if gstin:
        import re as _re
        valid_gstin = bool(_re.match(
            r'^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$', gstin
        ))
        if not valid_gstin:
            fraud_flags.append(
                f"Invalid GSTIN format: {gstin} — may be fake or AI-generated"
            )
            fraud_risk_score += 0.30
        else:
            fake_patterns = [
                r'[A-Z]{5}1234',
                r'AAAAA',
                r'ABCDE',
                r'DUMMY|DEMO|TEST|FAKE|SAMPLE|XXXXX',
            ]
            is_fake_gstin = any(
                _re.search(pat, gstin, _re.IGNORECASE)
                for pat in fake_patterns
            )
            if is_fake_gstin:
                fraud_flags.append(
                    f"Suspicious GSTIN detected: {gstin} — appears to be demo/test/fake"
                )
                fraud_risk_score += 0.35
    # RULE 7B-3 — Verify GSTIN via free lookup
    valid_gstin = valid_gstin if gstin else False
    if gstin and valid_gstin:
        try:
            import requests as _req
            response = _req.get(
                f"https://sheet.gst.gov.in/files/gstin/{gstin}",
                timeout=5
            )
            if response.status_code == 200:
                gst_data = response.json()
                status = gst_data.get("sts", "").lower()
                trade_name = gst_data.get("tradeNam", "")
                if "cancel" in status:
                    fraud_flags.append(
                        f"GSTIN {gstin} is CANCELLED — vendor '{trade_name}' inactive"
                    )
                    fraud_risk_score += 0.35
                # If 200 and active — GSTIN is real ✅
            elif response.status_code in [400, 404]:
                fraud_flags.append(
                    f"GSTIN {gstin} does not exist on GST portal — fake GSTIN"
                )
                fraud_risk_score += 0.50
        except Exception:
            pass  # Skip if portal unreachable — don't penalize
    # RULE 7C — Demo/test invoice detection
    demo_keywords = ['demo', 'test', 'sample', 'dummy', 'fake', 'example']
    receipt_no_str = str(receipt_number or "").lower()
    if any(kw in receipt_no_str for kw in demo_keywords):
        fraud_flags.append(
            f"Demo/test receipt number detected: {receipt_number}"
        )
        fraud_risk_score += 0.40

    # ── RULE 8 — AI-generated / fake invoice detection ───────────────────────
    ai_signals = 0

    # Signal A: OCR confidence suspiciously perfect
    if ocr_confidence >= 0.98:
        ai_signals += 1

    # Signal B: Total ends in .00
    if total_amount > 0:
        total_str = str(total_amount)
        if "." in total_str and total_str.split(".")[1] == "00":
            ai_signals += 1

    # Signal C: GSTIN present but no tax charged
    if gstin and tax_amount == 0:
        ai_signals += 1

    # Signal D: All line item prices perfectly round
    if line_items:
        perfect_prices = sum(
            1 for item in line_items
            if item.get("unit_price") and str(item["unit_price"]).endswith(".0")
        )
        if len(line_items) > 0 and perfect_prices == len(line_items):
            ai_signals += 1

    # Signal E: Future transaction date
    if transaction_date:
        try:
            txn_date = datetime.strptime(transaction_date, "%Y-%m-%d")
            if txn_date > datetime.now():
                fraud_flags.append(
                    f"Future transaction date: {transaction_date} — possible fake bill"
                )
                fraud_risk_score += 0.40
        except ValueError:
            pass

    # Signal F: Missing vendor address and GSTIN
    vendor_address = extracted_data.get("vendor_address") or extracted_data.get("location")
    if not vendor_address and not gstin:
        ai_signals += 1

    # Signal G: All line item totals end in 99 or 00
    if line_items and len(line_items) >= 2:
        round_prices = sum(
            1 for item in line_items
            if item.get("total_price") and (
                int(item["total_price"]) % 100 == 0 or
                int(item["total_price"]) % 100 == 99
            )
        )
        if round_prices == len(line_items):
            ai_signals += 1

    # Signal H: Receipt number looks auto-generated
    import re as _re2
    if receipt_number:
        auto_pattern = _re2.match(
            r'^[A-Z]{2,10}(-[A-Z]{2,5})?-\d{4}\d{0,4}-\d{2}-\d{3,10}$',
            str(receipt_number)
        )
        if auto_pattern:
            ai_signals += 1

    # Accumulate AI-generated risk
    if ai_signals >= 3:
        fraud_flags.append(
            f"Possible AI-generated or fabricated invoice — "
            f"{ai_signals} suspicious patterns detected "
            f"(perfect OCR, clean amounts, missing details)"
        )
        fraud_risk_score += 0.55
    elif ai_signals == 2:
        fraud_flags.append(
            "Invoice has multiple characteristics of a digitally generated/fake bill "
            "— verify authenticity"
        )
        fraud_risk_score += 0.40
    elif ai_signals == 1:
        fraud_flags.append(
            "Invoice has one suspicious pattern — manual verification recommended"
        )
        fraud_risk_score += 0.15

    fraud_risk_score = min(round(fraud_risk_score, 2), 1.0)
    requires_manual_review = fraud_risk_score >= 0.5

    return {
        "fraud_risk_score":       fraud_risk_score,
        "fraud_flags":            fraud_flags,
        "is_duplicate":           duplicate_check["is_duplicate"],
        "is_near_duplicate":      duplicate_check["is_near_duplicate"],
        "duplicate_match_id":     duplicate_check.get("duplicate_id"),
        "requires_manual_review": requires_manual_review,
        "review_reason":          ", ".join(fraud_flags) if fraud_flags else None
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
        "is_duplicate":      False,
        "is_near_duplicate": False,
        "duplicate_id":      None,
        "duplicate_date":    None
    }

    if not vendor_name or not total_amount:
        return result

    try:
        ninety_days_ago = datetime.now() - timedelta(days=90)

        recent_expenses = db.query(Expense).filter(
            Expense.user_id    == user_id,
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
                result["is_duplicate"]   = True
                result["duplicate_id"]   = expense.id
                result["duplicate_date"] = str(expense.created_at)[:10]
                return result

            # Check 2 — Same vendor + same amount + same date = exact duplicate
            if (
                expense.total_amount     == total_amount and
                expense.transaction_date == transaction_date
            ):
                result["is_duplicate"]   = True
                result["duplicate_id"]   = expense.id
                result["duplicate_date"] = str(expense.created_at)[:10]
                return result

            # Check 3 — Same vendor + amount within 5% = near duplicate
            if expense.total_amount:
                amount_diff_pct = abs(
                    expense.total_amount - total_amount
                ) / total_amount * 100

                if amount_diff_pct <= 5:
                    result["is_near_duplicate"] = True
                    result["duplicate_id"]       = expense.id
                    result["duplicate_date"]     = str(expense.created_at)[:10]

    except Exception:
        pass

    return result