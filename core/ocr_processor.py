
import io

import pymupdf
import pytesseract

from PIL import Image


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_pdf_text(uploaded_file):
    pdf_bytes = uploaded_file.getvalue()
    extracted_pages = []

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf"
    ) as document:

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            if text:
                extracted_pages.append(text)
                continue

            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False
            )

            image = Image.open(
                io.BytesIO(pix.tobytes("png"))
            )

            ocr_text = pytesseract.image_to_string(
                image,
                lang="eng",
                config="--psm 3"
            ).strip()

            extracted_pages.append(ocr_text)

    return "\n".join(extracted_pages)
