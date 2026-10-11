from datetime import datetime

import pandas as pd

from . import config


def clean_text(value):
    return " ".join(str(value).upper().split())


def clean_supplier(name):
    text = str(name).lower()
    for keyword, canonical in config.SUPPLIERS.items():
        if keyword in text:
            return canonical
    return clean_text(name)


def clean_unit(unit):
    text = str(unit).strip().lower()
    return config.UNITS.get(text, text.upper())


def to_base(qty, unit):
    if qty is None:
        return None, unit
    if unit == "YD":
        return round(qty * config.YARD_TO_METRE, 2), "M"
    return round(float(qty), 2), unit


def make_row(source, row_id, grn, date, supplier, item, lot, qty, unit, notes):
    unit = clean_unit(unit)
    base_qty, base_unit = to_base(qty, unit)
    return {
        "source": source,
        "row_id": row_id,
        "grn": grn,
        "date": date,
        "supplier": clean_supplier(supplier),
        "item": clean_text(item),
        "lot": clean_text(lot),
        "raw_qty": qty,
        "raw_unit": unit,
        "qty": base_qty,
        "unit": base_unit,
        "notes": notes,
    }


def load_register(pages):
    rows = []
    for page in pages:
        year = int(page["month"].split()[-1])
        for number, raw in enumerate(page["rows"], start=1):
            date = None
            if raw["date"]:
                day, month = raw["date"].split("/")
                date = datetime(year, int(month), int(day)).date().isoformat()
            grn = None
            if raw["grn"] is not None:
                grn = int(raw["grn"])
            notes = []
            for flag in raw["flags"]:
                notes.append(f"{flag['field']}: {flag['reason']}")
            row_id = f"REG-p{page['page']}-r{number}"
            rows.append(
                make_row("register", row_id, grn, date, raw["supplier"], raw["item"],
                         raw["lot"], raw["qty"], raw["unit"], notes)
            )
    return rows


def load_erp():
    data = pd.read_csv(config.ERP_FILE)
    rows = []
    for index, raw in data.iterrows():
        grn = int(str(raw["grn_no"]).replace("GRN-", ""))
        received = pd.to_datetime(raw["grn_date"]).date()
        entered = pd.to_datetime(raw["entered_at"]).date()
        notes = []
        days = (entered - received).days
        if days > config.LATE_ENTRY_DAYS:
            notes.append(f"entered {days} days after receipt, by {raw['entered_by']}")
        rows.append(
            make_row("erp", f"ERP-r{index + 2}", grn, received.isoformat(), raw["supplier_name"],
                     raw["item_desc"], raw["lot_no"], float(raw["qty"]), raw["uom"], notes)
        )
    return rows


def clean_sheet_date(value):
    if isinstance(value, str):
        return datetime.strptime(value.strip(), "%m/%d/%Y").date().isoformat()
    return pd.to_datetime(value).date().isoformat()


def load_sheet():
    data = pd.read_excel(config.SHEET_FILE)
    rows = []
    for index, raw in data.iterrows():
        grn = None
        if not pd.isna(raw["GRN"]):
            grn = int(raw["GRN"])
        notes = []
        if not pd.isna(raw["Remarks"]):
            notes.append(f"remark: {raw['Remarks']}")
        rows.append(
            make_row("sheet", f"XLS-r{index + 2}", grn, clean_sheet_date(raw["Date"]),
                     raw["Supplier"], raw["Material"], raw["Lot"], float(raw["Qty Received"]),
                     raw["UOM"], notes)
        )
    return rows


def save(register, erp, sheet):
    folder = config.OUTPUT / "clean"
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(register).to_csv(folder / "register.csv", index=False)
    pd.DataFrame(erp).to_csv(folder / "erp.csv", index=False)
    pd.DataFrame(sheet).to_csv(folder / "sheet.csv", index=False)
