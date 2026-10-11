import html

from . import config

STYLE = """
body { font-family: sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }
table { border-collapse: collapse; width: 100%; margin: 0.5rem 0; }
th, td { border: 1px solid #888; padding: 4px 8px; text-align: left; vertical-align: top; }
h2 { margin-top: 1.8rem; }
"""

OUTCOME_NAMES = [
    ("MATCHED", "matched"),
    ("MISMATCH", "mismatched"),
    ("MISSING", "missing from a source"),
    ("DUPLICATE", "duplicate"),
    ("NO_GRN", "without a GRN number"),
]


def table(headers, rows):
    text = "<table><tr>"
    for header in headers:
        text += f"<th>{html.escape(str(header))}</th>"
    text += "</tr>"
    for row in rows:
        text += "<tr>"
        for value in row:
            text += f"<td>{html.escape(str(value))}</td>"
        text += "</tr>"
    return text + "</table>"


def section(title, body):
    return f"<h2>{html.escape(title)}</h2>{body}"


def paragraph(text):
    return f"<p>{html.escape(text)}</p>"


def build(pages, rows_by_source, cases, tie, pending):
    flagged = 0
    for row in rows_by_source["register"]:
        flagged += len(row["notes"])

    counts = {}
    for case in cases:
        counts[case["outcome"]] = counts.get(case["outcome"], 0) + 1
    result = []
    for outcome, name in OUTCOME_NAMES:
        if outcome in counts:
            result.append(f"{counts[outcome]} {name}")

    tie_rows = []
    for line in tie:
        tie_rows.append([line["source"], line["input_rows"], line["outcome_rows"],
                         line["input_qty_total"], line["outcome_qty_total"], "yes" if line["ties"] else "NO"])

    pending_rows = []
    for record in pending:
        pending_rows.append([record["case_id"], record["outcome"], record["issue"]])

    page = f"<h1>Receiving reconciliation, {html.escape(pages[0]['month'])}</h1>"
    page += section("1. Read the photos", paragraph(
        f"{len(pages)} register pages were read, {len(rows_by_source['register'])} rows in total. "
        f"{flagged} cells were flagged because they were smudged or crossed out. Nothing was guessed."))
    page += section("2. Clean the data", paragraph(
        f"Dates, supplier names and units were put in one format. Rows read: register "
        f"{len(rows_by_source['register'])}, ERP {len(rows_by_source['erp'])}, "
        f"store sheet {len(rows_by_source['sheet'])}. Yards were changed to metres."))
    page += section("3. Match the three sources", paragraph(
        f"Rows were grouped by GRN number and compared. Result: {', '.join(result)}."))
    page += section("4. Check that nothing was lost", paragraph(
        "Every row of every source is in exactly one outcome. The counts and totals below "
        "are taken from the raw inputs and compared with the outcomes.")
        + table(["Source", "Input rows", "Outcome rows", "Input qty", "Outcome qty", "Ties"], tie_rows))
    if pending_rows:
        review = paragraph(f"{len(pending_rows)} items need a person. Open review.xlsx and fill in the decision column.")
        review += table(["Case", "Outcome", "Issue"], pending_rows)
    else:
        review = paragraph("Nothing needs a decision.")
    page += section("5. Review the doubtful items", review)
    page += section("6. Send the summary", paragraph(
        "A short email lists the top items and attaches review.xlsx. It is saved as summary.eml, "
        "and sent when the run uses --send."))

    text = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta name="color-scheme" content="light dark">'
            f"<title>Receiving reconciliation</title><style>{STYLE}</style></head><body>{page}</body></html>")
    path = config.OUTPUT / "report.html"
    path.write_text(text)
    return path
