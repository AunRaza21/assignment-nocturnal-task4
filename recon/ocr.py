import base64
import hashlib
import json
import os

import requests

from . import config

PROMPT = """This is a photo of a handwritten goods receiving register page.
Return JSON only, in this shape:
{"page": 1, "month": "Sep 2026", "rows": [
  {"date": "01/09", "grn": 4401, "supplier": "...", "item": "...", "lot": "...",
   "qty": 2000, "unit": "pcs", "received_by": "B.H.",
   "flags": [{"field": "qty", "reason": "..."}]}
]}
Rules:
- One entry per filled row, in order. Skip empty rows.
- Copy what is written. Do not guess.
- If a value is crossed out, use the new value and add a flag naming the old one.
- If a value is smudged or unreadable, set it to null and add a flag saying why.
- If you are unsure about a value, add a flag with the reason.
- grn and qty are numbers, everything else is text."""

ROW_KEYS = ["date", "grn", "supplier", "item", "lot", "qty", "unit", "flags"]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_manifest():
    if not config.MANIFEST.exists():
        return {}
    return json.loads(config.MANIFEST.read_text())


def check_page(page, name):
    if "month" not in page or not isinstance(page.get("rows"), list):
        raise ValueError(f"{name}: the OCR answer has no month or rows")
    for row in page["rows"]:
        for key in ROW_KEYS:
            if key not in row:
                raise ValueError(f"{name}: an OCR row is missing '{key}'")


def read_with_gemini(photo):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(f"{photo.name} is a new page and GEMINI_API_KEY is not set")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    image = base64.b64encode(photo.read_bytes()).decode()
    body = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image}},
                ]
            }
        ],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    response = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=120)
    response.raise_for_status()
    text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    page = json.loads(text)
    check_page(page, photo.name)
    return page


def load_pages():
    config.EXTRACTED.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()
    pages = []
    for photo in sorted(config.PHOTOS.glob("*.jpg")):
        digest = file_hash(photo)
        if digest in manifest:
            page = json.loads((config.EXTRACTED / manifest[digest]).read_text())
        else:
            print(f"New page {photo.name}: reading it with Gemini")
            page = read_with_gemini(photo)
            name = photo.stem + ".json"
            (config.EXTRACTED / name).write_text(json.dumps(page, indent=2) + "\n")
            manifest[digest] = name
            config.MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        pages.append(page)
    return pages
