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
            "description": "item name from Name of items column",
            "quantity": numeric — look for Quantity/Qty/Nos/Pcs/Units column,
            "unit_price": numeric — look for Rate/Price/MRP/Unit Price column,
            "total_price": numeric — look for Amount/Total/Value column
        }}
    ],
    "service_charge": numeric value of service charge if present or null,
    "extra_charges": numeric value of any other extra charges (packing, convenience etc.) or null,
    "confidence_score": a float between 0.0 and 1.0
}}

CRITICAL amount extraction rules:
- "total_amount" MUST be the FINAL payable amount — the LARGEST bottom-line total on the bill
- NEVER use subtotal/taxable value as total_amount
- For Indian GST invoices: total_amount = taxable_value + CGST + SGST + IGST combined
- Example: Taxable=456.78, IGST=82.22 → total_amount=539.00 (NOT 456.78)
- If the bill shows "INR 539.00" or "Grand Total 539.00" or "Total Amount 539.00" — that is total_amount
- subtotal = the pre-tax amount (taxable value / net amount before tax)
- tax_amount = total tax added (sum of ALL tax components: CGST + SGST + IGST + VAT etc.)
- When in doubt: total_amount = subtotal + tax_amount
- For food delivery bills: total_amount includes food subtotal + delivery fee + platform fee + all taxes
- NEVER ignore delivery charges or platform fees — they are part of total_amount
- "subtotal" for food delivery = food items total ONLY (before delivery/platform fees)
- Look for fields labeled: "Total Paid", "Grand Total", "Bill Total", "You Pay", "Order Total"
- The LAST and LARGEST number on the bill is almost always total_amount
- SERVICE CHARGE must be included in total_amount — it is NOT optional
- Formula for restaurant bills: total_amount = food subtotal + service charge + CGST + SGST
- Example: Subtotal=1150, Service Charge=115, CGST=28.75, SGST=28.75 → total_amount=1322.50
- Fields labeled "Service Charge", "SC", "Service Tax", "Convenience Fee" must be added to total
- IMPORTANT: Read the ENTIRE bill before deciding total_amount — do not stop at first subtotal
- Always scan for ALL extra charges: service charge, packing charge, convenience fee, delivery fee
- Add ALL of them to arrive at final total_amount
- tax_amount = sum of CGST + SGST + IGST + VAT only — do NOT include service charge in tax_amount

Line item extraction rules:
- The quantity column may be labeled: Quantity, Qty, Nos, Pcs, Units, No.
- The unit price column may be labeled: Rate, Price, MRP, Unit Price, Rate Rs
- The amount column may be labeled: Amount, Total, Value, Net Amount
- Always extract the actual number from the Quantity column, never default to 1
- If quantity column exists but value is missing for a row, use 1
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
        extracted_data = json.loads(response_text)

        # ── Post-processing: fix total_amount if AI still got it wrong ──────
        # Add service charge if AI missed it
        service_charge = extracted_data.get("service_charge") or 0
        if service_charge == 0:
            import re as _re3
            sc_match = _re3.search(
                r'service\s*charge[^\d]*([\d,]+\.?\d*)', ocr_text.lower()
            )
            if sc_match:
                try:
                    service_charge = float(sc_match.group(1).replace(",", ""))
                except ValueError:
                    service_charge = 0

        if service_charge > 0:
            current_total = extracted_data.get("total_amount") or 0
            sub_check = extracted_data.get("subtotal") or 0
            tax_check = extracted_data.get("tax_amount") or 0
            extra = extracted_data.get("extra_charges") or 0
            expected_with_sc = round(sub_check + service_charge + extra + tax_check, 2)
            if abs(current_total - expected_with_sc) > 1.0:
                extracted_data["total_amount"] = expected_with_sc
                print(f"SERVICE CHARGE FIX: added sc={service_charge} extra={extra} → new total {expected_with_sc}")

        # Scan raw OCR for largest currency amount first
        import re as _re2
        all_amounts = _re2.findall(r'(?:rs\.?|inr|₹)\s*([\d,]+\.?\d*)', ocr_text.lower())
        if all_amounts:
            parsed = []
            for a in all_amounts:
                try:
                    parsed.append(float(a.replace(",", "")))
                except ValueError:
                    pass
            if parsed:
                ocr_max = max(parsed)
                ai_total = extracted_data.get("total_amount") or 0
                if ocr_max > ai_total and ocr_max < ai_total * 2.5:
                    extracted_data["total_amount"] = ocr_max

        total  = extracted_data.get("total_amount") or 0
        sub    = extracted_data.get("subtotal") or 0
        tax    = extracted_data.get("tax_amount") or 0

        # If subtotal + tax = a number larger than total, AI used subtotal as total
        if sub > 0 and tax > 0:
            expected_total = round(sub + tax, 2)
            if abs(expected_total - total) > 0.5:          # mismatch of more than 50p
                extracted_data["total_amount"] = expected_total

        # If total < subtotal, something is definitely wrong — use subtotal+tax
        if sub > 0 and total < sub:
            extracted_data["total_amount"] = round(sub + (tax or 0), 2)

        # For food delivery / multi-charge bills (delivery fee, platform fee etc.)
        # Re-read after all corrections and keep largest value found
        final_total = extracted_data.get("total_amount") or 0
        recalc = round((sub or 0) + (tax or 0), 2)
        # If recalc is larger, AI missed extra charges — use recalc
        # If final_total is larger, it includes delivery/platform fees — keep it
        extracted_data["total_amount"] = max(final_total, recalc)
        
        return {"status": "success", "data": extracted_data}
    except json.JSONDecodeError as e:
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
    """
    Analyzes expense records and generates
    3 simple spending insights using Groq AI.
    """
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