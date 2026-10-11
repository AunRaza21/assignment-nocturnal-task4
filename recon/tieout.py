import pandas as pd

from . import config


class TieOutError(Exception):
    pass


def input_counts(pages):
    """Count rows and quantities straight from the raw inputs, before any cleaning."""
    register_qty = 0
    register_rows = 0
    for page in pages:
        for row in page["rows"]:
            register_rows += 1
            if row["qty"] is not None:
                register_qty += row["qty"]
    erp = pd.read_csv(config.ERP_FILE)
    sheet = pd.read_excel(config.SHEET_FILE)
    return {
        "register": (register_rows, register_qty),
        "erp": (len(erp), float(erp["qty"].sum())),
        "sheet": (len(sheet), float(sheet["Qty Received"].sum())),
    }


def outcome_counts(cases):
    counts = {}
    totals = {}
    seen = []
    for source in config.SOURCES:
        counts[source] = 0
        totals[source] = 0
    for case in cases:
        for row in case["rows"]:
            seen.append(row["row_id"])
            counts[row["source"]] += 1
            if row["raw_qty"] is not None:
                totals[row["source"]] += row["raw_qty"]
    return counts, totals, seen


def check(cases, pages):
    inputs = input_counts(pages)
    counts, totals, seen = outcome_counts(cases)

    problems = []
    repeated = []
    for row_id in seen:
        if seen.count(row_id) > 1 and row_id not in repeated:
            repeated.append(row_id)
    if repeated:
        problems.append("rows in more than one outcome (is a page photographed twice?): " + ", ".join(repeated[:5]))
    table = []
    for source in config.SOURCES:
        rows_in, qty_in = inputs[source]
        ok = rows_in == counts[source] and round(qty_in, 2) == round(totals[source], 2)
        if not ok:
            problems.append(f"{source}: input {rows_in} rows / {qty_in:g}, outcomes {counts[source]} rows / {totals[source]:g}")
        table.append({
            "source": source,
            "input_rows": rows_in,
            "outcome_rows": counts[source],
            "input_qty_total": round(qty_in, 2),
            "outcome_qty_total": round(totals[source], 2),
            "ties": ok,
        })
    if problems:
        raise TieOutError("; ".join(problems))
    return table


def save(cases, table):
    config.OUTPUT.mkdir(exist_ok=True)
    pd.DataFrame(table).to_csv(config.OUTPUT / "tieout.csv", index=False)
    rows = []
    for case in cases:
        for row in case["rows"]:
            rows.append({
                "source": row["source"],
                "row_id": row["row_id"],
                "case_id": case["case_id"],
                "outcome": case["outcome"],
            })
    pd.DataFrame(rows).to_csv(config.OUTPUT / "outcomes.csv", index=False)
