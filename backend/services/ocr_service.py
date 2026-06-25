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

            # Convert to numpy array and check variance
            img_array = np.array(image)

            # If variance is very low, image is blank or single color
            variance = np.var(img_array)
            if variance < 100:
                return {
                    "is_valid": False,
                    "reason": "Image appears to be blank or empty. Please upload a clear receipt photo."
                }

        except Exception as e:
            print(f"VALIDATE WARNING: Could not check image variance: {e}")
            # Don't reject — let OCR attempt it
            pass

    # Check 3 — PDF must have readable content
    if content_type == "application/pdf":
        if len(file_bytes) < 1000:
            return {
                "is_valid": False,
                "reason": "PDF file appears to be empty or corrupted."
            }

    return {"is_valid": True, "reason": None}
# ocr_service.py
# Updated to support:
# - Images: JPG, PNG, WEBP, TIFF, BMP
# - PDF files (using poppler + pdf2image)

import pytesseract
from PIL import Image
import io
import re
import os
if os.name == 'nt':  # Windows only
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Tell pytesseract where Tesseract is installed
#pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_bytes: bytes) -> dict:
    """
    Takes raw image bytes and extracts text using Tesseract OCR.
    Supports JPG, PNG, WEBP, TIFF, BMP formats.
    """
    import numpy as np

    # Convert raw bytes into PIL Image
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")

    # ── Image preprocessing to improve OCR accuracy ──────────────────────
    # Step 1: Upscale for better OCR on small text
    w, h = image.size
    if w < 1500:
        scale = 1500 / w
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Step 2: Convert to grayscale
    gray = image.convert("L")

    # Step 3: Increase contrast using numpy
    img_array = np.array(gray, dtype=np.float32)
    img_array = np.clip((img_array - 128) * 1.5 + 128, 0, 255).astype(np.uint8)
    gray = Image.fromarray(img_array)

    # Step 4: Apply threshold to make text sharper (binarization)
    threshold = 140
    gray = gray.point(lambda x: 0 if x < threshold else 255, '1')
    gray = gray.convert("L")

    # Use preprocessed image for OCR
    image = gray

    # Run OCR with better config for structured documents
    custom_config = r'--oem 3 --psm 6'
    raw_text = pytesseract.image_to_string(image, lang="eng", config=custom_config)
    # Get confidence data
    from pytesseract import Output
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    # Calculate average confidence
    confidences = [
        int(c) for c in data["conf"]
        if str(c).strip() != "-1" and str(c).strip() != ""
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    confidence_score = round(avg_confidence / 100, 2)

    # Clean the text
    cleaned_text = clean_ocr_text(raw_text)

    return {
        "raw_text": raw_text,
        "cleaned_text": cleaned_text,
        "confidence_score": confidence_score,
        "word_count": len(cleaned_text.split()),
        "source": "image"
    }


def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extracts text from a PDF file.
    Uses poppler to convert each page to an image,
    then runs Tesseract OCR on each page.
    """
    try:
        from pdf2image import convert_from_bytes
        import os
        poppler_path = None if os.name != 'nt' else r"C:\Users\ASUS\Downloads\Release-26.02.0-0\poppler\Library\bin"

        # Convert PDF pages to list of PIL Images
        # poppler_path tells pdf2image where poppler is installed
        images = convert_from_bytes(
            pdf_bytes,
            poppler_path=poppler_path
        )

        all_text = ""
        all_confidences = []

        # Run OCR on each page
        for i, image in enumerate(images):
            image = image.convert("RGB")

            # Extract text from this page
            page_text = pytesseract.image_to_string(image, lang="eng")
            all_text += f"\n--- Page {i+1} ---\n{page_text}"

            # Get confidence for this page
            from pytesseract import Output
            data = pytesseract.image_to_data(image, output_type=Output.DICT)
            confidences = [
                int(c) for c in data["conf"]
                if str(c).strip() != "-1" and str(c).strip() != ""
            ]
            if confidences:
                all_confidences.extend(confidences)

        # Calculate overall confidence
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
        confidence_score = round(avg_confidence / 100, 2)

        cleaned = clean_ocr_text(all_text)

        return {
            "raw_text": all_text,
            "cleaned_text": cleaned,
            "confidence_score": confidence_score,
            "word_count": len(cleaned.split()),
            "pages": len(images),
            "source": "pdf"
        }

    except Exception as e:
        return {
            "error": str(e),
            "raw_text": "",
            "cleaned_text": "",
            "confidence_score": 0.0,
            "word_count": 0,
            "source": "pdf"
        }


def clean_ocr_text(text: str) -> str:
    """
    Cleans up raw OCR output.
    Removes empty lines, fixes common OCR mistakes,
    and normalizes whitespace.
    """

    # Remove empty lines
    lines = text.split("\n")
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    cleaned = "\n".join(non_empty_lines)

    # Fix common OCR mistakes
    cleaned = cleaned.replace("|", "I")
    cleaned = cleaned.replace("{}", "0")

    # Remove multiple spaces
    cleaned = re.sub(r' +', ' ', cleaned)

    return cleaned