# ocr_service.py
# Updated to support:
# - Vision AI (Groq) — primary, most accurate
# - Images: JPG, PNG, WEBP, TIFF, BMP — Tesseract fallback
# - PDF files (using poppler + pdf2image) — Tesseract fallback

import pytesseract
from PIL import Image
import io
import re
import os

if os.name == 'nt':  # Windows only
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ═══════════════════════════════════════════════════════════════════════════════
# VISION AI OCR — Primary method (most accurate)
# ═══════════════════════════════════════════════════════════════════════════════

def extract_text_with_vision(image_bytes: bytes, content_type: str = "image/png") -> dict:
    """
    Use Groq Vision AI to extract text from image.
    Much more accurate than Tesseract for:
    - Colored backgrounds (blue/red table headers)
    - Styled fonts
    - Mixed layouts
    - Small text
    Falls back to None if API fails.
    """
    import base64
    import requests as _req

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    if not GROQ_API_KEY:
        print("VISION AI: No GROQ_API_KEY found, skipping")
        return None

    # Convert image to base64
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Ensure valid content type for vision
    if content_type not in ["image/jpeg", "image/jpg", "image/png", "image/webp"]:
        content_type = "image/png"

    prompt = """You are an OCR system. Extract ALL text from this invoice/receipt image exactly as it appears.

Include every number, label, amount, date, and text visible.
Pay special attention to:
- All monetary amounts (item prices, subtotals, totals, taxes, discounts)
- Table data row by row
- Grand Total / Total Amount / Net Payable at the bottom
- Invoice number, date, GSTIN
- Vendor name and address

Format: raw text line by line, preserving layout.
Do NOT summarize. Extract every single piece of text exactly as shown."""

    try:
        response = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{b64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            },
            timeout=30
        )

        if response.status_code == 200:
            text = response.json()["choices"][0]["message"]["content"]
            cleaned = clean_ocr_text(text)
            word_count = len(cleaned.split())
            print(f"VISION AI SUCCESS: {word_count} words extracted")
            return {
                "raw_text":        text,
                "cleaned_text":    cleaned,
                "confidence_score": 0.95,
                "word_count":      word_count,
                "source":          "vision_ai"
            }
        elif response.status_code == 429:
            print("VISION AI: Rate limit hit, falling back to Tesseract")
            return None
        else:
            print(f"VISION AI: Failed with status {response.status_code}, falling back to Tesseract")
            return None

    except Exception as e:
        print(f"VISION AI ERROR: {e} — falling back to Tesseract")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def validate_image_file(file_bytes: bytes, content_type: str) -> dict:
    """
    Validates a file before sending it to OCR.
    Prevents processing empty, blank, or invalid files.
    Returns a dict with is_valid and reason.
    """
    import numpy as np

    # Check 1 — File must not be empty
    if len(file_bytes) < 500:
        return {
            "is_valid": False,
            "reason": "File is too small or empty. Please upload a valid receipt image."
        }

    # Check 2 — For images, check if it's completely blank
    if content_type in ["image/jpeg", "image/png", "image/jpg", "image/webp"]:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image = image.convert("RGB")
            img_array = np.array(image)
            variance = np.var(img_array)
            if variance < 100:
                return {
                    "is_valid": False,
                    "reason": "Image appears to be blank or empty. Please upload a clear receipt photo."
                }
        except Exception as e:
            print(f"VALIDATE WARNING: Could not check image variance: {e}")
            pass

    # Check 3 — PDF must have readable content
    if content_type == "application/pdf":
        if len(file_bytes) < 1000:
            return {
                "is_valid": False,
                "reason": "PDF file appears to be empty or corrupted."
            }

    return {"is_valid": True, "reason": None}


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE OCR — Vision AI first, Tesseract fallback
# ═══════════════════════════════════════════════════════════════════════════════

def extract_text_from_image(image_bytes: bytes, content_type: str = "image/png") -> dict:
    """
    Extracts text from image.
    1st: Tries Vision AI (Groq) — handles colored backgrounds, styled fonts
    2nd: Falls back to Tesseract with preprocessing
    """
    import numpy as np

    # ── Step 1: Try Vision AI first ──────────────────────────────────────────
    vision_result = extract_text_with_vision(image_bytes, content_type)
    if vision_result and vision_result.get("word_count", 0) > 5:
        return vision_result

    print("VISION AI: Not available or insufficient text — using Tesseract")

    # ── Step 2: Tesseract with preprocessing ─────────────────────────────────
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")

    # Upscale for better OCR on small text
    w, h = image.size
    if w < 1500:
        scale = 1500 / w
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Convert to grayscale
    gray = image.convert("L")

    # Increase contrast
    img_array = np.array(gray, dtype=np.float32)
    img_array = np.clip((img_array - 128) * 2.0 + 128, 0, 255).astype(np.uint8)
    gray = Image.fromarray(img_array)

    # Sharpen
    from PIL import ImageFilter
    gray = gray.filter(ImageFilter.SHARPEN)
    gray = gray.filter(ImageFilter.SHARPEN)

    # Adaptive threshold
    img_arr = np.array(gray)
    avg_brightness = img_arr.mean()
    threshold = 100 if avg_brightness < 128 else 150
    gray = gray.point(lambda x: 0 if x < threshold else 255, '1')
    gray = gray.convert("L")

    # Run Tesseract
    custom_config = r'--oem 3 --psm 6'
    raw_text = pytesseract.image_to_string(gray, lang="eng", config=custom_config)

    # Get confidence
    from pytesseract import Output
    data = pytesseract.image_to_data(gray, output_type=Output.DICT)
    confidences = [
        int(c) for c in data["conf"]
        if str(c).strip() != "-1" and str(c).strip() != ""
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    confidence_score = round(avg_confidence / 100, 2)

    cleaned_text = clean_ocr_text(raw_text)

    return {
        "raw_text":        raw_text,
        "cleaned_text":    cleaned_text,
        "confidence_score": confidence_score,
        "word_count":      len(cleaned_text.split()),
        "source":          "tesseract"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PDF OCR — Vision AI per page, Tesseract fallback
# ═══════════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extracts text from PDF.
    Converts each page to image, then tries Vision AI, falls back to Tesseract.
    """
    try:
        from pdf2image import convert_from_bytes
        poppler_path = None if os.name != 'nt' else r"C:\Users\ASUS\Downloads\Release-26.02.0-0\poppler\Library\bin"

        images = convert_from_bytes(pdf_bytes, poppler_path=poppler_path)

        all_text      = ""
        all_confidences = []

        for i, image in enumerate(images):
            image = image.convert("RGB")

            # Convert page to bytes for Vision AI
            page_buf = io.BytesIO()
            image.save(page_buf, format="PNG")
            page_bytes = page_buf.getvalue()

            # Try Vision AI first
            vision_result = extract_text_with_vision(page_bytes, "image/png")
            if vision_result and vision_result.get("word_count", 0) > 5:
                page_text = vision_result["raw_text"]
                all_confidences.append(95)
                print(f"VISION AI: PDF page {i+1} — {vision_result['word_count']} words")
            else:
                # Fall back to Tesseract
                page_text = pytesseract.image_to_string(image, lang="eng")
                from pytesseract import Output
                data = pytesseract.image_to_data(image, output_type=Output.DICT)
                confidences = [
                    int(c) for c in data["conf"]
                    if str(c).strip() != "-1" and str(c).strip() != ""
                ]
                if confidences:
                    all_confidences.extend(confidences)
                print(f"TESSERACT: PDF page {i+1} fallback")

            all_text += f"\n--- Page {i+1} ---\n{page_text}"

        avg_confidence  = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        confidence_score = round(avg_confidence / 100, 2)
        if confidence_score > 1.0:
            confidence_score = 0.95

        cleaned = clean_ocr_text(all_text)

        return {
            "raw_text":        all_text,
            "cleaned_text":    cleaned,
            "confidence_score": confidence_score,
            "word_count":      len(cleaned.split()),
            "pages":           len(images),
            "source":          "pdf"
        }

    except Exception as e:
        return {
            "error":           str(e),
            "raw_text":        "",
            "cleaned_text":    "",
            "confidence_score": 0.0,
            "word_count":      0,
            "source":          "pdf"
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TEXT CLEANING
# ═══════════════════════════════════════════════════════════════════════════════

def clean_ocr_text(text: str) -> str:
    """
    Cleans up raw OCR output.
    Removes empty lines, fixes common OCR mistakes,
    and normalizes whitespace.
    """
    lines = text.split("\n")
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    cleaned = "\n".join(non_empty_lines)

    # Fix common OCR mistakes
    cleaned = cleaned.replace("|", "I")
    cleaned = cleaned.replace("{}", "0")

    # Remove multiple spaces
    cleaned = re.sub(r' +', ' ', cleaned)

    return cleaned