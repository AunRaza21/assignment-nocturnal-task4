import openpyxl

from recon import clean, match, ocr, review, tieout


def build():
    pages = ocr.load_pages()
    register = clean.load_register(pages)
    erp = clean.load_erp()
    sheet = clean.load_sheet()
    return pages, match.reconcile(register, erp, sheet)


def find(cases, case_id):
    for case in cases:
        if case["case_id"] == case_id:
            return case
    raise AssertionError(f"{case_id} not found")


def test_every_row_lands_in_exactly_one_outcome():
    pages, cases = build()
    table = tieout.check(cases, pages)
    assert len(table) == 3
    for line in table:
        assert line["ties"]


def test_known_problems_are_found():
    pages, cases = build()
    assert find(cases, "GRN-4421")["outcome"] == "MISSING"
    assert find(cases, "GRN-4430")["outcome"] == "MISSING"
    assert find(cases, "GRN-4417")["highlight"] == ["erp"]
    assert find(cases, "GRN-4412")["outcome"] == "MISMATCH"
    assert find(cases, "GRN-4425")["highlight"] == ["sheet"]
    assert "sheet" in find(cases, "GRN-4419")["highlight"]
    assert find(cases, "GRN-4428")["review"]
    assert find(cases, "XLS-r31")["outcome"] == "NO_GRN"
    assert find(cases, "GRN-4401")["outcome"] == "MATCHED"


def test_identical_duplicate_is_handled_without_review():
    pages, cases = build()
    duplicate = find(cases, "DUP-XLS-r11")
    assert duplicate["outcome"] == "DUPLICATE"
    assert not duplicate["review"]


def test_running_twice_gives_the_same_result():
    first = build()[1]
    second = build()[1]
    assert first == second


def test_decisions_survive_a_rerun(tmp_path):
    path = tmp_path / "review.xlsx"
    cases = build()[1]
    review.write_review(cases, path)

    book = openpyxl.load_workbook(path)
    sheet = book.active
    sheet.cell(row=2, column=review.HEADERS.index("decision") + 1).value = "accept_erp"
    book.save(path)

    applied, errors = review.apply_decisions(path)
    assert applied == 1 and errors == []

    review.write_review(cases, path)
    assert len(review.read_pending(path)) == 8
