
from pathlib import Path
import json
import os
import re

from dotenv import load_dotenv
from neo4j import GraphDatabase


# STEP 1: Load Neo4j AuraDB configuration
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv(
    "NEO4J_DATABASE", "neo4j"
)

EXTRACTED_DIR = Path("data/extracted")
MANIFEST_FILE = Path("data/manifest.json")


# STEP 2: Define known entities and aliases
CROP_ENTITIES = {
    "Paddy": ["paddy", "rice", "நெல்"],
    "Sugarcane": ["sugarcane", "கரும்பு"],
    "Cotton": ["cotton", "பருத்தி"],
    "Groundnut": ["groundnut", "நிலக்கடலை"],
    "Millet": ["millet", "சிறுதானியம்"],
    "Banana": ["banana", "வாழை"]
}

# These are illustrative vocabulary entries.
# Confirm names against downloaded documents.
SCHEME_ENTITIES = {
    "Collective Farming": [
        "collective farming"
    ],
    "TNMSDD": [
        "tamilnadu mission for sustainable dry land",
        "tnmsdd"
    ]
}


# STEP 3: Find entity mentions in page text
def find_entities(text, vocabulary):
    matches = set()

    for canonical_name, aliases in vocabulary.items():
        for alias in aliases:

            if alias.isascii():
                # Avoid English substring false matches.
                pattern = (
                    r"(?<!\w)"
                    + re.escape(alias)
                    + r"(?!\w)"
                )
                found = re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE
                )
            else:
                found = alias in text

            if found:
                matches.add(canonical_name)
                break

    return sorted(matches)


# STEP 4: Read source URLs from scraper manifest
def load_source_urls():

    if not MANIFEST_FILE.exists():
        return {}

    rows = json.loads(
        MANIFEST_FILE.read_text(encoding="utf-8")
    )

    return {
        item["filename"]: item.get("url", "")
        for item in rows
    }


# STEP 5: Create Neo4j constraints
def create_constraints(driver):

    queries = [
        """
        CREATE CONSTRAINT document_id IF NOT EXISTS
        FOR (d:Document)
        REQUIRE d.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT page_id IF NOT EXISTS
        FOR (p:Page)
        REQUIRE p.id IS UNIQUE
        """,
        """
        CREATE CONSTRAINT crop_name IF NOT EXISTS
        FOR (c:Crop)
        REQUIRE c.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT scheme_name IF NOT EXISTS
        FOR (s:Scheme)
        REQUIRE s.name IS UNIQUE
        """
    ]

    for cypher in queries:
        driver.execute_query(
            cypher,
            database_=NEO4J_DATABASE
        )


# STEP 6: Upload one document and its pages
def upload_document(driver, document, source_urls):

    document_id = document["document_id"]
    filename = document["filename"]
    source_url = source_urls.get(filename, "")

    # Create or update the document node.
    driver.execute_query(
        """
        MERGE (d:Document {id: $document_id})
        SET d.filename = $filename,
            d.source_url = $source_url,
            d.total_pages = $total_pages,
            d.processed_at = $processed_at
        """,
        document_id=document_id,
        filename=filename,
        source_url=source_url,
        total_pages=document["total_pages"],
        processed_at=document["processed_at"],
        database_=NEO4J_DATABASE
    )

    # Prepare page data and extracted entities.
    rows = []

    for page in document["pages"]:

        text = page.get("text", "")
        page_number = page["page_number"]

        crops = find_entities(
            text, CROP_ENTITIES
        )

        schemes = find_entities(
            text, SCHEME_ENTITIES
        )

        rows.append({
            "page_id": f"{document_id}:{page_number}",
            "page_number": page_number,
            "text": text,
            "method": page["extraction_method"],
            "crops": crops,
            "schemes": schemes
        })

    # Upload all pages and page relationships.
    driver.execute_query(
        """
        MATCH (d:Document {id: $document_id})
        UNWIND $rows AS row

        MERGE (p:Page {id: row.page_id})
        SET p.number = row.page_number,
            p.text = row.text,
            p.method = row.method

        MERGE (d)-[:HAS_PAGE]->(p)
        """,
        document_id=document_id,
        rows=rows,
        database_=NEO4J_DATABASE
    )

    # STEP 7: Create crop entities and links.
    driver.execute_query(
        """
        UNWIND $rows AS row
        MATCH (p:Page {id: row.page_id})

        UNWIND row.crops AS crop_name

        MERGE (c:Crop {name: crop_name})

        MERGE (p)-[:MENTIONS_CROP]->(c)
        """,
        rows=rows,
        database_=NEO4J_DATABASE
    )

    # STEP 8: Create scheme entities and links.
    driver.execute_query(
        """
        UNWIND $rows AS row
        MATCH (p:Page {id: row.page_id})

        UNWIND row.schemes AS scheme_name

        MERGE (s:Scheme {name: scheme_name})

        MERGE (p)-[:MENTIONS_SCHEME]->(s)
        """,
        rows=rows,
        database_=NEO4J_DATABASE
    )

    print(
        f"Uploaded: {filename} | "
        f"Pages: {len(rows)}"
    )


# STEP 9: Main workflow
def main():

    if not all([
        NEO4J_URI,
        NEO4J_USER,
        NEO4J_PASSWORD
    ]):
        raise ValueError(
            "Missing Neo4j credentials in .env"
        )

    files = sorted(
        EXTRACTED_DIR.glob("*.json")
    )

    if not files:
        print("No extracted JSON files found.")
        return

    source_urls = load_source_urls()

    with GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    ) as driver:

        driver.verify_connectivity()
        print("Connected to Neo4j AuraDB!")

        create_constraints(driver)

        for filepath in files:
            try:
                document = json.loads(
                    filepath.read_text(
                        encoding="utf-8"
                    )
                )

                upload_document(
                    driver,
                    document,
                    source_urls
                )

            except Exception as error:
                print(
                    "Upload failed:",
                    filepath.name,
                    error
                )

    print("Graph building completed!")


if __name__ == "__main__":
    main()
