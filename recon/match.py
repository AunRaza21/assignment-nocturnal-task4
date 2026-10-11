from . import config

NAMES = {"register": "register", "erp": "ERP", "sheet": "sheet"}


def number_text(value):
    if value == int(value):
        return str(int(value))
    return str(value)


def qty_text(row):
    if row["raw_qty"] is None:
        return "unreadable"
    text = number_text(row["raw_qty"]) + " " + row["raw_unit"]
    if row["raw_unit"] != row["unit"]:
        text += f" (= {number_text(row['qty'])} {row['unit']})"
    return text


def field_text(row, field):
    if field == "qty":
        return qty_text(row)
    return str(row[field])


def row_text(row):
    parts = [str(row["date"]), row["supplier"], row["item"], row["lot"], qty_text(row)]
    return " | ".join(parts)


def differing_fields(rows):
    fields = []
    for field in config.COMPARE_FIELDS:
        values = set()
        for row in rows:
            values.add(row[field])
        if len(values) > 1:
            fields.append(field)
    return fields


def odd_sources(main, present, field):
    """Return the sources that disagree with a clear majority, and the majority value."""
    counts = {}
    for source in present:
        value = main[source][field]
        if value is not None:
            counts[value] = counts.get(value, 0) + 1
    if not counts:
        return list(present), None
    best = max(counts.values())
    winners = []
    for value, count in counts.items():
        if count == best:
            winners.append(value)
    if len(winners) == 1 and best >= 2:
        odd = []
        for source in present:
            if main[source][field] != winners[0]:
                odd.append(source)
        return odd, winners[0]
    return list(present), None


def names_text(sources):
    names = []
    for source in sources:
        names.append(NAMES[source])
    return ", ".join(names)


def score(outcome, fields, notes):
    if outcome == "MISSING":
        points = 100
    elif outcome == "MISMATCH":
        points = 50
        if "qty" in fields:
            points += 10
    elif outcome == "NO_GRN":
        points = 40
    else:
        points = 30
    for note in notes:
        if "unreadable" in note or "crossed out" in note or "after receipt" in note:
            points += 20
    return points


def make_case(case_id, grn, outcome, rows, display, issue, suggestion, highlight, review, fields, notes):
    return {
        "case_id": case_id,
        "grn": grn,
        "outcome": outcome,
        "rows": rows,
        "display": display,
        "issue": issue,
        "suggestion": suggestion,
        "highlight": highlight,
        "review": review,
        "score": score(outcome, fields, notes),
    }


def no_grn_case(row):
    source = row["source"]
    display = {}
    for name in config.SOURCES:
        display[name] = "-"
    display[source] = row_text(row)
    issue = f"{NAMES[source]} row has no GRN number"
    for note in row["notes"]:
        issue += f" ({note})"
    suggestion = "Nothing to match on without a GRN number: a person decides what it is"
    return make_case(row["row_id"], None, "NO_GRN", [row], display, issue, suggestion,
                     [source], True, [], row["notes"])


def duplicate_case(grn, source, first, extra):
    fields = differing_fields([first, extra])
    display = {}
    for name in config.SOURCES:
        display[name] = "-"
    display[source] = row_text(extra)
    issue = f"GRN {grn} appears twice in the {NAMES[source]}"
    if fields:
        issue += ", with different " + ", ".join(fields)
        suggestion = "The two entries disagree: check which one is right"
    else:
        issue += ", with identical values"
        suggestion = "Ignore the extra row"
    return make_case("DUP-" + extra["row_id"], grn, "DUPLICATE", [extra], display, issue,
                     suggestion, [source], len(fields) > 0, fields, [])


def main_case(grn, main):
    present = []
    missing = []
    for source in config.SOURCES:
        if main[source]:
            present.append(source)
        else:
            missing.append(source)
    rows = []
    notes = []
    for source in present:
        rows.append(main[source])
        for note in main[source]["notes"]:
            notes.append(f"{NAMES[source]} {note}")
    fields = differing_fields(rows)

    issues = []
    suggestions = []
    highlight = list(missing)
    if missing:
        issues.append("missing from " + names_text(missing))
        suggestions.append("Confirm the delivery happened, then add the missing entry")
    for field in fields:
        parts = []
        for source in present:
            parts.append(f"{NAMES[source]} {field_text(main[source], field)}")
        issues.append(f"{field}: " + ", ".join(parts))
        odd, right = odd_sources(main, present, field)
        highlight += odd
        if right is None:
            suggestions.append(f"{field}: cannot tell which is right, check the paper delivery note")
        elif main[odd[0]][field] is None:
            suggestions.append(f"{field}: {names_text(odd)} is unreadable, the others agree")
        else:
            suggestions.append(f"{field}: {names_text(odd)} looks wrong, the others agree")
    issues += notes

    if missing:
        outcome = "MISSING"
    elif fields:
        outcome = "MISMATCH"
    else:
        outcome = "MATCHED"
    review = outcome != "MATCHED" or len(notes) > 0

    display = {}
    for source in config.SOURCES:
        if main[source]:
            display[source] = row_text(main[source])
        else:
            display[source] = "MISSING"
    return make_case(f"GRN-{grn}", grn, outcome, rows, display, "; ".join(issues),
                     "; ".join(suggestions), highlight, review, fields, notes)


def reconcile(register, erp, sheet):
    groups = {}
    cases = []
    for rows in (register, erp, sheet):
        for row in rows:
            if row["grn"] is None:
                cases.append(no_grn_case(row))
                continue
            if row["grn"] not in groups:
                groups[row["grn"]] = {"register": [], "erp": [], "sheet": []}
            groups[row["grn"]][row["source"]].append(row)

    for grn in sorted(groups):
        main = {}
        for source in config.SOURCES:
            rows = groups[grn][source]
            main[source] = rows[0] if rows else None
            for extra in rows[1:]:
                cases.append(duplicate_case(grn, source, rows[0], extra))
        cases.append(main_case(grn, main))
    return cases
