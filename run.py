import argparse
import sys

from recon import clean, match, notify, ocr, report, review, tieout


def apply_review():
    applied, errors = review.apply_decisions()
    print(f"Review decisions applied: {applied}")
    for error in errors:
        print(f"  Not applied - {error}")
    return errors


def run(send):
    pages = ocr.load_pages()
    register = clean.load_register(pages)
    erp = clean.load_erp()
    sheet = clean.load_sheet()
    clean.save(register, erp, sheet)

    apply_review()

    cases = match.reconcile(register, erp, sheet)
    table = tieout.check(cases, pages)
    tieout.save(cases, table)
    review.write_review(cases)

    print("\nTie-out (inputs vs outcomes)")
    for line in table:
        print(f"  {line['source']:9} rows {line['input_rows']} = {line['outcome_rows']}, "
              f"qty {line['input_qty_total']:g} = {line['outcome_qty_total']:g}")

    pending = review.read_pending()
    print(f"\nPending review items: {len(pending)}")

    rows_by_source = {"register": register, "erp": erp, "sheet": sheet}
    print(f"Report saved to {report.build(pages, rows_by_source, cases, table, pending)}")

    message = notify.build_email(pending, table, pages[0]["month"])
    print(f"Summary saved to {notify.save_email(message)}")
    if send:
        notify.send_email(message)


def main():
    parser = argparse.ArgumentParser(description="Three-way register reconciliation")
    parser.add_argument("--send", action="store_true", help="email the summary through Gmail")
    args = parser.parse_args()

    try:
        run(args.send)
    except (RuntimeError, ValueError, tieout.TieOutError) as error:
        print(f"Stopped: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
