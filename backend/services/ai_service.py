from groq import Groq
import json
import re
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# AMOUNT EXTRACTION — pure OCR math, no AI guessing
# ═══════════════════════════════════════════════════════════════════════════════

def extract_total_from_ocr(ocr_text: str) -> float:
    """
    Extract the final total amount directly from OCR text using regex patterns.
    This is more reliable than asking AI to calculate it.
    Handles all bill types: GST, non-GST, delivery, service charge, discounts.
    """
    text = ocr_text.lower()
    lines = text.split('\n')

    # ── Priority 1: Find explicit total labels (most reliable) ──────────────
    # These patterns match the actual bottom-line total on any bill
    total_patterns = [
        r'(?:grand\s*total|net\s*payable|amount\s*due|total\s*amount\s*due|bill\s*total|you\s*pay|total\s*payable|amount\s*payable|final\s*total|total\s*bill)[^\d]*([\d,]+\.?\d*)',
        r'total\s*paid[^\d]*rs\.?\s*([\d,]+\.?\d*)',
        r'total\s*paid[^\d]*([\d,]+\.?\d*)',
        r'rs\.?\s*([\d,]+\.?\d*)\s*(?:grand\s*total|net\s*payable)',
    ]
    # Also scan line by line for total labels
    for line in lines:
        line_clean = line.strip()
        if any(kw in line_clean for kw in [
            'grand total', 'total paid', 'net payable', 'amount due',
            'bill total', 'you pay', 'total payable', 'net amount payable'
        ]):
            nums = re.findall(r'[\d,]+\.\d{2}', line_clean)
            for n in reversed(nums):
                try:
                    val = float(n.replace(',', ''))
                    if val > 10:
                        return val
                except:
                    pass
    for pattern in total_patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
        for m in matches:
            try:
                val = float(m.replace(',', ''))
                if val > 0:
                    return val
            except:
                pass

    # ── Priority 2: Find "Rs X" or "INR X" on lines containing total keywords ─
    for line in lines:
        if any(kw in line for kw in ['grand total', 'total paid', 'net payable', 'amount due', 'bill total', 'you pay']):
            nums = re.findall(r'[\d,]+\.?\d*', line)
            for n in reversed(nums):  # last number on line is usually the amount
                try:
                    val = float(n.replace(',', ''))
                    if val > 10:  # ignore tiny numbers
                        return val
                except:
                    pass

    # ── Priority 3: Scan for Rs/INR amounts and return the largest ───────────
    # Works for bills where total is just the biggest number
    amount_patterns = [
        r'rs\.?\s*([\d,]+\.?\d*)',
        r'inr\.?\s*([\d,]+\.?\d*)',
        r'₹\s*([\d,]+\.?\d*)',
        r'rs\s*([\d,]+\.\d{2})',
    ]
    all_amounts = []
    for pattern in amount_patterns:
        for m in re.findall(pattern, text):
            try:
                val = float(m.replace(',', ''))
                if val > 1:
                    all_amounts.append(val)
            except:
                pass

    if all_amounts:
        return max(all_amounts)

    return 0.0


def extract_components_from_ocr(ocr_text: str) -> dict:
    """
    Extract all bill components from OCR text using regex.
    """
    text = ocr_text.lower()
    result = {
        'subtotal': 0.0, 'tax': 0.0, 'cgst': 0.0, 'sgst': 0.0,
        'igst': 0.0, 'vat': 0.0, 'discount': 0.0, 'delivery': 0.0,
        'platform': 0.0, 'service': 0.0, 'packing': 0.0, 'convenience': 0.0,
    }

    def find_amount(pattern, text):
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1).replace(',', ''))
                return val if 0 < val < 1000000 else 0.0
            except:
                return 0.0
        return 0.0

    def find_line_amount(line):
        """Get the last number on a line — usually the amount."""
        nums = re.findall(r'[\d,]+\.\d{2}', line)
        for n in reversed(nums):
            try:
                val = float(n.replace(',', ''))
                if val > 0:
                    return val
            except:
                pass
        return 0.0

    lines = text.split('\n')

    # ── Subtotal ─────────────────────────────────────────────────────────────
    subtotal_keywords = ['sub total', 'subtotal', 'item total', 'net amount',
                         'taxable value', 'taxable amount', 'basic amount']
    for line in lines:
        if any(kw in line for kw in subtotal_keywords):
            val = find_line_amount(line)
            if val > result['subtotal']:
                result['subtotal'] = val

    # ── Tax lines ─────────────────────────────────────────────────────────────
    cgst_total, sgst_total, igst_total, vat_total = 0.0, 0.0, 0.0, 0.0
    gst_lines_total = 0.0

    for line in lines:
        if 'cgst' in line:
            val = find_line_amount(line)
            if 0 < val < 50000:
                cgst_total += val
        if 'sgst' in line:
            val = find_line_amount(line)
            if 0 < val < 50000:
                sgst_total += val
        if 'igst' in line:
            val = find_line_amount(line)
            if 0 < val < 50000:
                igst_total += val
        if 'vat' in line and 'taxable' not in line:
            val = find_line_amount(line)
            if 0 < val < 50000:
                vat_total += val
        # GST lines (not CGST/SGST/IGST)
        if 'gst' in line and 'cgst' not in line and 'sgst' not in line and 'igst' not in line and 'gstin' not in line and 'breakup' not in line:
            val = find_line_amount(line)
            if 0 < val < 50000:
                gst_lines_total += val

    tax_from_components = cgst_total + sgst_total + igst_total + vat_total
    result['tax'] = max(tax_from_components, gst_lines_total)
    result['cgst'] = cgst_total
    result['sgst'] = sgst_total
    result['igst'] = igst_total
    result['vat']  = vat_total

    # ── Discount — CRITICAL: must not pick up item prices ────────────────────
    # Only look for lines that explicitly mention discount keywords
    discount_keywords = ['discount', 'zomato gold', 'swiggy one', 'coupon',
                         'promo', 'cashback', 'offer', 'savings', 'voucher']
    for line in lines:
        if any(kw in line for kw in discount_keywords):
            # Skip lines that are just label rows with no amount
            val = find_line_amount(line)
            # Sanity check: discount should be less than subtotal
            sub = result['subtotal']
            if val > 0 and (sub == 0 or val < sub * 0.8):
                if val > result['discount']:
                    result['discount'] = val

    # Also catch "-Rs X" style discounts
    neg_matches = re.findall(r'-\s*(?:rs\.?)?\s*([\d,]+\.\d{2})', text)
    for m in neg_matches:
        try:
            val = float(m.replace(',', ''))
            sub = result['subtotal']
            if val > 0 and (sub == 0 or val < sub * 0.8):
                if val > result['discount']:
                    result['discount'] = val
        except:
            pass

    # ── Extra charges ─────────────────────────────────────────────────────────
    for line in lines:
        if 'delivery fee' in line or 'delivery charge' in line:
            val = find_line_amount(line)
            if 0 < val < 5000:
                result['delivery'] = val
        if 'platform fee' in line:
            val = find_line_amount(line)
            if 0 < val < 5000:
                result['platform'] = val
        if 'packing' in line and 'charge' in line:
            val = find_line_amount(line)
            if 0 < val < 5000:
                result['packing'] = val
        if 'convenience fee' in line:
            val = find_line_amount(line)
            if 0 < val < 5000:
                result['convenience'] = val
        if 'service charge' in line or 'service tax' in line:
            val = find_line_amount(line)
            if 0 < val < 50000:
                result['service'] = val

    return result

def calculate_best_total(ocr_text: str, ai_total: float, ai_subtotal: float, ai_tax: float) -> float:
    """
    Calculate the most accurate total using multiple strategies.
    Returns the best total amount.
    """
    # Strategy 1: Direct OCR extraction (most reliable)
    ocr_total = extract_total_from_ocr(ocr_text)

    # Strategy 2: Component-based calculation
    components = extract_components_from_ocr(ocr_text)
    sub  = components['subtotal'] or ai_subtotal or 0
    tax  = components['tax'] or ai_tax or 0
    disc = components['discount']
    extra = (components['delivery'] + components['platform'] +
             components['packing'] + components['convenience'])
    sc   = components['service']

    calc_total = 0.0
    # Only use subtotal in calc if it's reasonable (OCR sometimes misreads large numbers)
    # If subtotal looks wrong (too small compared to tax), skip it
    if sub > 0 and (tax == 0 or sub > tax * 0.5):
        calc_total = round(sub - disc + extra + sc + tax, 2)
    elif tax > 0:
        # Fallback: if we have tax but no reliable subtotal, use AI subtotal
        ai_sub = ai_subtotal or 0
        if ai_sub > tax:
            calc_total = round(ai_sub - disc + extra + sc + tax, 2)

    print(f"AMOUNT STRATEGIES: ocr={ocr_total} calc={calc_total} ai={ai_total}")
    print(f"COMPONENTS: sub={sub} tax={tax} disc={disc} extra={extra} sc={sc}")

    # Decision logic:
    # 1. If OCR found explicit total label → trust it most
    # 2. If calc matches OCR → perfect
    # 3. If calc is reasonable → use calc
    # 4. Fall back to AI

    if ocr_total > 0:
        # OCR found an explicit total
        if calc_total > 0 and abs(calc_total - ocr_total) < 5:
            # Both agree — use OCR (directly extracted)
            return ocr_total
        elif calc_total > 0 and calc_total > ocr_total * 0.8 and calc_total < ocr_total * 1.2:
            # Close enough — trust OCR
            return ocr_total
        else:
            # They disagree — use whichever is larger (OCR total labels are reliable)
            return ocr_total

    if calc_total > 0:
        return calc_total

    if ai_total > 0:
        return ai_total

    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXTRACTION FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_expense_data(ocr_text: str) -> dict:
    prompt = f"""
You are an AI that extracts structured data from receipt/bill text.
Extract the following fields from the receipt text below.
If a field cannot be found, use null.
Return ONLY a valid JSON object with these exact fields:
{{
    "vendor_name": "name of the shop or business",
    "transaction_date": "date in YYYY-MM-DD format",
    "total_amount": the final payable amount at the bottom of the bill as a numeric value,
    "subtotal": numeric value of item total before tax/charges or null,
    "tax_amount": sum of ALL tax lines (CGST+SGST+IGST+VAT+GST on delivery) or null,
    "tax_type": "GST or VAT or null",
    "currency_code": "INR or USD etc",
    "payment_method": "Cash or UPI or Card or Unknown",
    "receipt_number": "bill/invoice number or null",
    "gstin": "GST Identification Number if present or null",
    "vendor_category_hint": "type of business e.g. restaurant, pharmacy, fuel station, grocery store or null",
    "line_items": [
        {{
            "description": "item name",
            "quantity": numeric,
            "unit_price": numeric,
            "total_price": numeric
        }}
    ],
    "service_charge": numeric value of service charge if present or null,
    "extra_charges": sum of delivery fee + platform fee + packing charge or null,
    "discount_amount": total discount deducted as positive number or null,
    "confidence_score": float between 0.0 and 1.0
}}

Rules:
- total_amount = the GRAND TOTAL / TOTAL PAID / NET PAYABLE shown at the bottom
- subtotal = item total before any tax, discount, or extra charges
- tax_amount = CGST + SGST + IGST + VAT + all GST lines added together
- discount_amount = any discount/offer subtracted (always positive)
- extra_charges = delivery fee + platform fee + packing charge added together
- service_charge = restaurant service charge only

{ocr_text}
Return ONLY the JSON object. No explanation. No markdown. No backticks.
"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()
        response_text = response_text.replace('\t', ' ')

        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError:
            response_text = re.sub(r'[\x00-\x1f\x7f]', ' ', response_text)
            response_text = re.sub(r',\s*}', '}', response_text)
            response_text = re.sub(r',\s*]', ']', response_text)
            extracted_data = json.loads(response_text)

        # ── Post-processing: Override AI total with our reliable calculation ──
        ai_total    = extracted_data.get("total_amount") or 0
        ai_subtotal = extracted_data.get("subtotal") or 0
        ai_tax      = extracted_data.get("tax_amount") or 0

        best_total = calculate_best_total(ocr_text, ai_total, ai_subtotal, ai_tax)

        if best_total > 0 and abs(best_total - ai_total) > 0.5:
            print(f"TOTAL OVERRIDE: AI said {ai_total}, using {best_total}")
            extracted_data["total_amount"] = best_total

        # Also fix tax_amount if AI missed some tax lines
        components = extract_components_from_ocr(ocr_text)
        ocr_tax = components['tax']
        if ocr_tax > 0 and abs(ocr_tax - ai_tax) > 0.5:
            print(f"TAX OVERRIDE: AI said {ai_tax}, using {ocr_tax}")
            extracted_data["tax_amount"] = ocr_tax

        # Fix extra_charges if AI missed delivery/platform fees
        ocr_extra = (components['delivery'] + components['platform'] +
                     components['packing'] + components['convenience'])
        ai_extra = extracted_data.get("extra_charges") or 0
        if ocr_extra > 0 and ocr_extra > ai_extra:
            extracted_data["extra_charges"] = ocr_extra

        # Fix discount if AI missed it
        ocr_disc = components['discount']
        ai_disc  = extracted_data.get("discount_amount") or 0
        if ocr_disc > 0 and ocr_disc > ai_disc:
            extracted_data["discount_amount"] = ocr_disc

        # Fix service charge if AI missed it
        ocr_sc = components['service']
        ai_sc  = extracted_data.get("service_charge") or 0
        if ocr_sc > 0 and ocr_sc > ai_sc:
            extracted_data["service_charge"] = ocr_sc

        return {"status": "success", "data": extracted_data}

    except json.JSONDecodeError as e:
        try:
            retry_response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "user", "content": f"Extract expense data from this receipt text. Return ONLY valid JSON, no markdown:\n\n{ocr_text[:2000]}"}
                ],
                temperature=0.0,
                max_tokens=800
            )
            retry_text = retry_response.choices[0].message.content.strip()
            if retry_text.startswith("```"):
                retry_text = re.sub(r'^```[a-z]*\n?', '', retry_text)
                retry_text = re.sub(r'\n?```$', '', retry_text)
            retry_text = re.sub(r'[\x00-\x1f\x7f]', ' ', retry_text.strip())
            retry_text = re.sub(r',\s*}', '}', retry_text)
            retry_text = re.sub(r',\s*]', ']', retry_text)
            extracted_data = json.loads(retry_text)
            # Apply our total fix on retry too
            ai_total    = extracted_data.get("total_amount") or 0
            ai_subtotal = extracted_data.get("subtotal") or 0
            ai_tax      = extracted_data.get("tax_amount") or 0
            best_total  = calculate_best_total(ocr_text, ai_total, ai_subtotal, ai_tax)
            if best_total > 0:
                extracted_data["total_amount"] = best_total
            return {"status": "success", "data": extracted_data}
        except Exception:
            return {"status": "error", "error": f"Failed to parse AI response: {str(e)}"}
    except Exception as e:
        return {"status": "error", "error": f"AI service error: {str(e)}"}


def classify_expense(vendor_name: str, line_items: list, vendor_hint: str = None) -> dict:
    items_text = ""
    if line_items:
        items_text = ", ".join([
            item.get("description", "")
            for item in line_items
            if item.get("description")
        ])
    prompt = f"""
You are an expense classification engine.
Classify this expense into one of these primary categories:
- Food & Dining
- Travel & Transport
- Health & Medical
- Office & Supplies
- Utilities
- Entertainment
- Shopping
- Education
- Finance
- Miscellaneous
Vendor: {vendor_name}
Items purchased: {items_text}
Vendor type hint: {vendor_hint or 'unknown'}
Return ONLY a valid JSON object:
{{
    "primary_category": "category name from the list above",
    "subcategory": "specific subcategory",
    "classification_confidence": float between 0.0 and 1.0,
    "classification_reasoning": "one sentence explanation"
}}
Return ONLY the JSON. No explanation. No markdown. No backticks.
"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()
        classification = json.loads(response_text)
        return {"status": "success", "data": classification}
    except Exception as e:
        return {"status": "error", "error": f"Classification error: {str(e)}"}


def generate_expense_report(expenses: list) -> dict:
    expense_summary = json.dumps(expenses[:20], indent=2)
    prompt = f"""
You are an expense analytics assistant.
Given these expense records, generate a concise report.
Return ONLY a valid JSON object:
{{
    "total_spend": numeric total of all amounts,
    "transaction_count": number of expenses,
    "average_transaction": numeric average amount,
    "top_category": "category with highest spend",
    "top_vendor": "vendor with highest spend",
    "insights": ["insight 1", "insight 2", "insight 3"],
    "recommendations": ["recommendation 1", "recommendation 2"]
}}
Expense records:
{expense_summary}
Return ONLY the JSON. No explanation. No markdown. No backticks.
"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()
        report = json.loads(response_text)
        return {"status": "success", "data": report}
    except Exception as e:
        return {"status": "error", "error": f"Report generation error: {str(e)}"}


def generate_insights(expenses: list) -> dict:
    if not expenses:
        return {
            "status": "success",
            "data": {
                "insights": [
                    "No expenses found yet. Start by scanning your first receipt.",
                    "Upload receipts to get personalized spending insights.",
                    "XpenseIQ will analyze your patterns once you add expenses."
                ]
            }
        }

    total = sum(e.get("total_amount", 0) or 0 for e in expenses)
    categories = {}
    vendors = {}
    for e in expenses:
        cat    = e.get("primary_category", "Unknown")
        vendor = e.get("vendor_name", "Unknown")
        amount = e.get("total_amount", 0) or 0
        categories[cat]    = categories.get(cat, 0) + amount
        vendors[vendor]    = vendors.get(vendor, 0) + amount

    top_category = max(categories, key=categories.get) if categories else "Unknown"
    top_vendor   = max(vendors,    key=vendors.get)    if vendors    else "Unknown"
    top_cat_pct  = round(categories.get(top_category, 0) / total * 100) if total else 0

    prompt = f"""
You are an expense analytics assistant.
Analyze this spending summary and give exactly 3 short, helpful insights.
Each insight should be one sentence with specific numbers.

Total spend: Rs {total:.0f}
Number of transactions: {len(expenses)}
Top category: {top_category} ({top_cat_pct}% of spend)
Top vendor: {top_vendor}
Category breakdown: {categories}

Return ONLY a valid JSON object:
{{
    "insights": [
        "insight 1 with specific numbers",
        "insight 2 with specific numbers",
        "insight 3 with specific numbers"
    ]
}}
Return ONLY the JSON. No explanation. No markdown. No backticks.
"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()
        data = json.loads(response_text)
        return {"status": "success", "data": data}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "insights": [
                    f"Your top spending category is {top_category} at {top_cat_pct}% of total spend.",
                    f"Your most visited vendor is {top_vendor}.",
                    f"You have {len(expenses)} approved transactions totaling Rs {total:.0f}."
                ]
            }
        }


def check_groq_usage() -> dict:
    """Check if Groq API is working."""
    import requests as _req
    try:
        response = _req.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=5
        )
        if response.status_code == 200:
            return {"status": "ok", "message": "Groq API is working fine"}
        elif response.status_code == 429:
            return {"status": "rate_limited", "message": "Daily token limit reached"}
        else:
            return {"status": "error", "message": f"Status: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}