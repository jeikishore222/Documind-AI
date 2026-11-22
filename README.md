# DocuMind AI

**AI-Powered Procurement Document Verification System**

DocuMind AI is a Python-based application that extracts, analyzes, and verifies information from Purchase Orders (PO), Supplier Invoices, and Goods Receipt Notes (GRN).

It helps identify mismatched quantities, prices, and financial discrepancies across procurement documents.

## Features

- PDF document processing and text extraction
- OCR support for scanned documents
- AI-assisted data extraction using Ollama and Llama 3.2
- Purchase Order, Invoice, and GRN comparison
- Quantity and price mismatch detection
- Financial discrepancy calculations
- Source-grounded extraction validation
- PDF, CSV, and JSON report generation
- SQLite verification history
- Streamlit analytics dashboard
- Automated verification tests

## Technology Stack

- **Language:** Python 3.13
- **Frontend:** Streamlit
- **AI Model:** Llama 3.2 3B
- **Local AI Runtime:** Ollama
- **PDF Processing:** PyMuPDF
- **OCR:** Tesseract and Pytesseract
- **Data Validation:** Pydantic
- **Data Analysis:** Pandas
- **Visualization:** Matplotlib
- **Database:** SQLite
- **Report Generation:** ReportLab
- **Testing:** Pytest

## Installation

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Documind-AI
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the actual repository URL after publishing.

### 2. Create a virtual environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
```

### 4. Set up Ollama

Install Ollama from https://ollama.com.

Download the AI model:

```powershell
ollama pull llama3.2:3b
```

Ensure the Ollama service is running locally at `http://localhost:11434`.

### 5. Set up Tesseract OCR

Install Tesseract OCR and ensure its executable is accessible to the application.

## Run the Application

```powershell
python -m streamlit run app.py
```

Open the local URL displayed by Streamlit.

## Run Automated Tests

```powershell
python -m pytest core/tests -v
```

## Project Structure

```text
Documind-AI/
├── app.py
├── core/
│   ├── column_layout.py
│   ├── extraction_checker.py
│   ├── llm_extractor.py
│   ├── ocr_processor.py
│   ├── schemas.py
│   ├── source_grounding.py
│   ├── verifier.py
│   └── tests/
├── database/
│   └── db_manager.py
├── reports/
│   └── report_generator.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Testing

The project has passed 27 automated tests covering extraction validation, source grounding, and document verification.

It has also been tested with sample procurement documents containing different table layouts.

## Limitations

Document extraction accuracy depends on PDF layout, scan quality, OCR performance, and AI model responses. Verification results should be reviewed before making financial or operational decisions.

## Privacy

The application uses a locally hosted Ollama model and stores verification history in a local SQLite database. Sensitive documents, databases, and generated reports should not be committed to public repositories.

## Project Status

Working portfolio implementation with document verification, reporting, analytics, and automated tests.