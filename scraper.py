
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
import hashlib
import json
import os
import time

import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

#START_URL = "https://www.tnagrisnet.tn.gov.in/home/gos"
START_URL = "https://agritech.tnau.ac.in/tnau_publish.html"
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET = int(os.getenv("PDF_TARGET", "100"))
MAX_PAGES = 50

# Only crawl this government portal.
ALLOWED_HOST = urlparse(START_URL).hostname

def normalize_url(base, href):
    if not href:
        return None

    url = urldefrag(urljoin(base, href))[0]
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return None

    if parsed.hostname != ALLOWED_HOST:
        return None

    return url


def discover_links():
    pdf_candidates = set()
    visited = set()
    pending = [START_URL]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        while pending and len(visited) < MAX_PAGES:
            url = pending.pop(0)

            if url in visited:
                continue

            visited.add(url)
            print("Crawling:", url)

            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )

                page.wait_for_timeout(1500)

                links = page.locator("a[href]").evaluate_all(
                    """elements => elements.map(a => ({
                        href: a.getAttribute('href'),
                        text: a.innerText || ''
                    }))"""
                )

                for item in links:
                    link = normalize_url(
                        page.url, item["href"]
                    )

                    if not link:
                        continue

                    label = item["text"].lower()
                    path = urlparse(link).path.lower()

                    if (
                        ".pdf" in link.lower()
                        or "download" in path
                        or (
                            "pdf" in label
                            and "javascript:" not in link
                        )
                    ):
                        pdf_candidates.add(link)

                    elif (
                        link not in visited
                        and link not in pending
                        and (
                            "/home/" in path
                            or "page=" in link
                        )
                    ):
                        pending.append(link)

            except Exception as exc:
                print("Page error:", exc)

        browser.close()

    return sorted(pdf_candidates)


def download_pdfs(urls):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "AgricultureKGResearch/1.0"
    })

    manifest = []
    seen_hashes = set()

    for url in urls:
        if len(manifest) >= TARGET:
            break

        try:
            response = session.get(
                url, timeout=60
            )
            response.raise_for_status()

            content = response.content

            # Validate real PDF content.
            if not content.lstrip()[:5] == b"%PDF-":
                print("Not a PDF:", url)
                continue

            digest = hashlib.sha256(content).hexdigest()

            if digest in seen_hashes:
                continue

            seen_hashes.add(digest)

            filename = f"{digest[:16]}.pdf"
            filepath = OUTPUT_DIR / filename
            filepath.write_bytes(content)

            manifest.append({
                "filename": filename,
                "url": url,
                "sha256": digest
            })

            print(
                f"Downloaded {len(manifest)}/{TARGET}:",
                filename
            )

            time.sleep(0.5)

        except Exception as exc:
            print("Download failed:", url, exc)

    Path("data/manifest.json").write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print("Total downloaded:", len(manifest))


if __name__ == "__main__":
    links = discover_links()
    print("Candidate links:", len(links))
    download_pdfs(links)
