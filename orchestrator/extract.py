"""Pulls the text out of an uploaded story file."""
from io import BytesIO

from docx import Document
from pypdf import PdfReader

MAX_CHARS = 12000  # about 2,000 words: plenty for a campfire story


def extract_text(filename: str, data: bytes) -> str:
    """Return the text of a .txt, .docx, or .pdf file."""
    name = filename.lower()

    if name.endswith(".txt"):
        text = data.decode("utf-8", errors="replace")
    elif name.endswith(".docx"):
        document = Document(BytesIO(data))
        text = "\n\n".join(p.text for p in document.paragraphs if p.text.strip())
    elif name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError("Please upload a .txt, .docx, or .pdf file")

    text = text.strip()
    if not text:
        raise ValueError("That file doesn't seem to have any text in it")
    return text[:MAX_CHARS]