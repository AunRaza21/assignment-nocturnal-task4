import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if value.strip():
            os.environ.setdefault(name.strip(), value.strip())


load_env()

RAW = ROOT / "data" / "raw"
PHOTOS = RAW / "register"
ERP_FILE = RAW / "t4_erp_grn.csv"
SHEET_FILE = RAW / "t4_store_sheet.xlsx"
EXTRACTED = ROOT / "data" / "extracted"
MANIFEST = EXTRACTED / "manifest.json"
OUTPUT = ROOT / "output"
REVIEW_FILE = OUTPUT / "review.xlsx"

SOURCES = ["register", "erp", "sheet"]
COMPARE_FIELDS = ["date", "supplier", "item", "lot", "qty", "unit"]

TOP_N = 3
LATE_ENTRY_DAYS = 2
YARD_TO_METRE = 0.9144

DECISIONS = ["ACCEPT_REGISTER", "ACCEPT_ERP", "ACCEPT_SHEET", "IGNORE", "ESCALATE"]

# A keyword found in the supplier name maps to one canonical name.
SUPPLIERS = {
    "qasr": "Qasr Packaging",
    "taraz": "Taraz Poly",
    "zarnab": "Zarnab Chemical",
    "rehbar": "Rehbar Threads",
    "saahil": "Saahil Pallets",
    "nayab": "Nayab Labels",
    "shahtoot": "Shahtoot Weaving",
}

UNITS = {
    "pcs": "PCS",
    "bag": "BAG",
    "bags": "BAG",
    "cone": "CONE",
    "cones": "CONE",
    "drum": "DRUM",
    "drums": "DRUM",
    "roll": "ROLL",
    "rolls": "ROLL",
    "ctn": "CTN",
    "ctns": "CTN",
    "bdl": "BDL",
    "m": "M",
    "yd": "YD",
    "yds": "YD",
}
