from groq import Groq
import json
import re
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)


def extract_expense_data(ocr_text: str) -> dict:
    prompt = f"""
You are an AI that extracts structured data from receipt/bill text.
Extract the following fields from the receipt text below.
If a field cannot be found, use null.
Return ONLY a valid JSON object with these exact fields:
{{
    "vendor_name": "name of the shop or business",
    "transaction_date": "date in YYYY-MM-DD format",
    "total_amount": numeric value only,
    "subtotal": numeric value only or null,
    "tax_amount": numeric value only or null,
    "tax_type": "GST or VAT or null",
    "currency_code": "INR or USD etc",
    "payment_method": "Cash or UPI or Card or Unknown",
    "receipt_number": "bill/invoice number or null",
    "gstin": "GST Identification Number if present on receipt or null",
    "vendor_category_hint": "type of business e.g. restaurant, pharmacy, fuel station or null",
    "line_items": [
        {{
            "description": "item name",
            "quantity": numeric,
            "unit_price": numeric,
            "total_price": numeric
        }}
    ],
    "service_charge": numeric value of service charge if present or null,
    "extra_charges": numeric value of delivery fee + platform fee + packing charge combined or null,
    "discount_amount": numeric value of total discount deducted — always positive number or null,
    "confidence_score": a float between 0.0 and 1.0
}}

CRITICAL amount extraction rules:
- "total_amount" MUST be the FINAL payable amount shown at the bottom of the bill
- Look for: "Total Paid", "Grand Total", "Net Payable", "Bill Total", "You Pay", "Amount Due"
- That bottom-line number IS total_amount — extract it directly, do not recalculate
- subtotal = food/item total ONLY before any additions or deductions
- tax_amount = sum of ALL tax lines (CGST + SGST + IGST + VAT + GST on delivery)
- service_charge = service charge amount only
- extra_charges = delivery fee + platform fee + packing charge + convenience fee (sum all)
- discount_amount = total discount/offer deducted (positive number e.g. 87.50 not -87.50)
- Formula check: subtotal - discount + extra_charges + service_charge + tax_amount = total_amount

Line item extraction rules:
- Quantity column: Quantity, Qty, Nos, Pcs, Units
- Unit price column: Rate, Price, MRP, Unit Price
- Amount column: Amount, Total, Value, Net Amount
- unit_price x quantity should approximately equal total_price

{ocr_text}
Return ONLY the JSON object. No explanation. No markdown. No backticks.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```[a-z]*\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()
        # Clean common JSON-breaking characters from response
        response_text = response_text.replace('\t', ' ')
        # Fix unescaped quotes inside string values
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try aggressive cleaning
            response_text = re.sub(r'[\x00-\x1f\x7f]', ' ', response_text)
            response_text = re.sub(r',\s*}', '}', response_text)
            response_text = re.sub(r',\s*]', ']', response_text)
            extracted_data = json.loads(response_text)

        # ── Post-processing: fix total_amount ──────────────────────────────
        import re as _re

        sub      = extracted_data.get("subtotal") or 0
        tax      = extracted_data.get("tax_amount") or 0
        sc       = extracted_data.get("service_charge") or 0
        extra    = extracted_data.get("extra_charges") or 0
        discount = extracted_data.get("discount_amount") or 0
        ai_total = extracted_data.get("total_amount") or 0

        # Step 1: Extract missing values from OCR text
        if sc == 0:
            m = _re.search(r'service\s*charge[^\d]*([\d,]+\.?\d*)', ocr_text.lower())
            if m:
                try: sc = float(m.group(1).replace(",", ""))
                except: sc = 0

        if discount == 0:
            m = _re.search(
                r'(?:discount|zomato gold|swiggy one|coupon|savings|offer)[^\d]*([\d,]+\.?\d*)',
                ocr_text.lower()
            )
            if m:
                try: discount = float(m.group(1).replace(",", ""))
                except: discount = 0

        if extra == 0:
            delivery = 0
            platform = 0
            packing  = 0
            m = _re.search(r'delivery\s*(?:fee|charge)[^\d]*([\d,]+\.?\d*)', ocr_text.lower())
            if m:
                try: delivery = float(m.group(1).replace(",", ""))
                except: delivery = 0
            m = _re.search(r'platform\s*fee[^\d]*([\d,]+\.?\d*)', ocr_text.lower())
            if m:
                try: platform = float(m.group(1).replace(",", ""))
                except: platform = 0
            m = _re.search(r'packing\s*(?:fee|charge)[^\d]*([\d,]+\.?\d*)', ocr_text.lower())
            if m:
                try: packing = float(m.group(1).replace(",", ""))
                except: packing = 0
            extra = delivery + platform + packing

        # Step 2: Find all currency amounts in OCR
        all_amounts = _re.findall(r'(?:rs\.?|inr|₹)\s*([\d,]+\.\d{2})', ocr_text.lower())
        parsed_amounts = []
        for a in all_amounts:
            try: parsed_amounts.append(float(a.replace(",", "")))
            except: pass

        # Step 3: Calculate expected total from components
        if sub > 0:
            expected = round(sub - discount + extra + sc + tax, 2)
        else:
            expected = 0

        ocr_max = max(parsed_amounts) if parsed_amounts else 0

        print(f"TOTAL DEBUG: ai={ai_total} sub={sub} tax={tax} sc={sc} extra={extra} discount={discount} expected={expected} ocr_max={ocr_max}")

        # Step 4: Pick best total
        # Priority: expected calculation > OCR max > AI total
        if expected > 0 and abs(expected - ai_total) > 1.0:
            # Our calculation differs from AI — trust our math
            extracted_data["total_amount"] = expected
            print(f"TOTAL FIX (calc): {ai_total} → {expected}")
        elif ocr_max > 0 and ocr_max > ai_total and ocr_max < ai_total * 2.0:
            # OCR found a larger reasonable amount
            extracted_data["total_amount"] = ocr_max
            print(f"TOTAL FIX (ocr): {ai_total} → {ocr_max}")
        elif sub > 0 and ai_total < sub:
            # Total is less than subtotal — definitely wrong
            extracted_data["total_amount"] = round(sub + tax + sc + extra - discount, 2)
            print(f"TOTAL FIX (sub>total): {ai_total} → {extracted_data['total_amount']}")

        return {"status": "success", "data": extracted_data}

    except json.JSONDecodeError as e:
        # Retry once with stricter prompt
        try:
            retry_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": f"Extract expense data from this text and return ONLY valid JSON with no special characters in string values:\n\n{ocr_text[:2000]}"}
                ],
                temperature=0.0,
                max_tokens=1000
            )
            retry_text = retry_response.choices[0].message.content.strip()
            if retry_text.startswith("```"):
                retry_text = re.sub(r'^```[a-z]*\n?', '', retry_text)
                retry_text = re.sub(r'\n?```$', '', retry_text)
            retry_text = re.sub(r'[\x00-\x1f\x7f]', ' ', retry_text.strip())
            retry_text = re.sub(r',\s*}', '}', retry_text)
            retry_text = re.sub(r',\s*]', ']', retry_text)
            extracted_data = json.loads(retry_text)
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
            model="llama-3.3-70b-versatile",
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
            model="llama-3.3-70b-versatile",
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
        cat = e.get("primary_category", "Unknown")
        vendor = e.get("vendor_name", "Unknown")
        amount = e.get("total_amount", 0) or 0
        categories[cat] = categories.get(cat, 0) + amount
        vendors[vendor] = vendors.get(vendor, 0) + amount

    top_category = max(categories, key=categories.get) if categories else "Unknown"
    top_vendor = max(vendors, key=vendors.get) if vendors else "Unknown"
    top_cat_pct = round(categories.get(top_category, 0) / total * 100) if total else 0

    prompt = f"""
You are an expense analytics assistant.
Analyze this spending summary and give exactly 3 short, helpful insights.
Each insight should be one sentence. Be specific with numbers.

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
            model="llama-3.3-70b-versatile",
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