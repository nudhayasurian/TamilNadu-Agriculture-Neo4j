
from pathlib import Path
import pymupdf

IMAGE_DIR = Path("data/images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

for filepath in Path("data/raw").glob("*.pdf"):
    with pymupdf.open(filepath) as doc:
        for page_no, page in enumerate(doc, start=1):
            for image_no, image in enumerate(
                page.get_images(full=True), start=1
            ):
                xref = image[0]
                data = doc.extract_image(xref)

                extension = data["ext"]
                filename = (
                    f"{filepath.stem}_p{page_no}"
                    f"_img{image_no}.{extension}"
                )

                output = IMAGE_DIR / filename
                output.write_bytes(data["image"])

                print("Extracted:", output)
