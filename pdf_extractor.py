
from pathlib import Path
from datetime import datetime, timezone
import io
import json
import os
import hashlib

import pymupdf
import pytesseract
from PIL import Image
from dotenv import load_dotenv


# STEP 1: Load environment configuration
load_dotenv()

tesseract_cmd = os.getenv("TESSERACT_CMD")

if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = (
        tesseract_cmd
    )


# STEP 2: Define input and output folders
RAW_DIR = Path("data/raw")
EXTRACTED_DIR = Path("data/extracted")

RAW_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)


# STEP 3: Extract text from one PDF page
def extract_page_text(page):

    # First attempt: normal PDF text extraction
    text = page.get_text("text").strip()

    if len(text) >= 50:
        return text, "direct"

    # Second attempt: OCR scanned page
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )

    image = Image.open(
        io.BytesIO(pix.tobytes("png"))
    )

    ocr_text = pytesseract.image_to_string(
        image,
        lang="tam+eng",
        config="--psm 3"
    ).strip()

    # Keep whichever extraction has more content.
    if len(ocr_text) > len(text):
        return ocr_text, "ocr"

    return text, "direct"


# STEP 4: Process an entire PDF
def extract_pdf(pdf_path):

    print(f"\nProcessing: {pdf_path.name}")

    pdf_bytes = pdf_path.read_bytes()

    document_id = hashlib.sha256(
        pdf_bytes
    ).hexdigest()

    extracted_pages = []

    with pymupdf.open(pdf_path) as pdf:

        total_pages = len(pdf)

        for page_index in range(total_pages):

            page = pdf[page_index]

            text, method = extract_page_text(page)

            page_data = {
                "page_number": page_index + 1,
                "text": text,
                "extraction_method": method,
                "character_count": len(text)
            }

            extracted_pages.append(page_data)

            print(
                f"Page {page_index + 1}/{total_pages}"
                f" | Method: {method}"
                f" | Characters: {len(text)}"
            )

    result = {
        "document_id": document_id,
        "filename": pdf_path.name,
        "total_pages": len(extracted_pages),
        "processed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "pages": extracted_pages
    }

    return result


# STEP 5: Save extracted text as JSON
def save_json(result):

    output_path = (
        EXTRACTED_DIR /
        f"{result['document_id']}.json"
    )

    output_path.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("JSON saved:", output_path)


# STEP 6: Process all downloaded PDFs
def main():

    pdf_files = sorted(RAW_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No PDFs found in data/raw")
        return

    print("Total PDFs found:", len(pdf_files))

    success = 0
    failed = 0

    for pdf_path in pdf_files:

        try:
            result = extract_pdf(pdf_path)
            save_json(result)
            success += 1

        except Exception as error:
            print(
                "Failed:",
                pdf_path.name,
                str(error)
            )
            failed += 1

    print("\nExtraction completed")
    print("Successful:", success)
    print("Failed:", failed)


if __name__ == "__main__":
    main()
