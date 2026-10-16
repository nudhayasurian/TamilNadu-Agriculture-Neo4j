
# Tamil Nadu Agriculture Knowledge Graph

A Python-based multimodal Knowledge Graph project
that collects Tamil Nadu Government agriculture PDFs,
extracts Tamil and English text using OCR,
identifies entities and relationships,
and stores them in Neo4j AuraDB Cloud.

## Technology Stack

- Python
- Playwright
- PyMuPDF
- Tesseract OCR (Tamil + English)
- Neo4j AuraDB Cloud
- Streamlit
- NetworkX
- PyVis

## Architecture

Government Agriculture Website
        |
        v
Playwright PDF Scraper
        |
        v
PDF Extraction + OCR
        |
        v
Entity Extraction
        |
        v
Relationship Mapping
        |
        v
Neo4j AuraDB Cloud
        |
        v
Streamlit Dashboard

## Project Structure

- scraper.py - Downloads PDF files
- pdf_extractor.py - Extracts PDF text using OCR
- graph_builder.py - Builds the knowledge graph
- app.py - Streamlit UI
- data/raw/ - Downloaded PDFs
- data/extracted/ - Extracted JSON files

## Installation

1. Create Python virtual environment:

   python -m venv venv

2. Activate:

   venv\Scripts\activate

3. Install dependencies:

   pip install -r requirements.txt

4. Install Playwright Chromium:

   python -m playwright install chromium

5. Install Tesseract OCR with English and Tamil.

## Neo4j Cloud Configuration

Create a .env file with:

NEO4J_URI=neo4j+s://YOUR_INSTANCE.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_PASSWORD
NEO4J_DATABASE=neo4j
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

Never commit the .env file.

## Execution

Download documents:

    python scraper.py

Extract PDF text:

    python pdf_extractor.py

Build knowledge graph:

    python graph_builder.py

Launch dashboard:

    streamlit run app.py

## Neo4j Validation

Run in Neo4j Query:

    MATCH (n)
    RETURN labels(n), count(n);

## Current Features

- PDF discovery and downloading
- Tamil and English OCR
- Page-level text extraction
- Rule-based entity extraction
- Neo4j cloud graph storage
- Streamlit document search
- Graph visualization

## Planned Enhancements

- LLM-based entity extraction
- Audio and video ingestion
- Image and chart understanding
- Graph-RAG chatbot
- Automated ingestion pipeline

## Notes

The target is approximately 100 agriculture PDFs.
Actual downloads depend on source availability.
Always verify extracted information against
original government documents.
