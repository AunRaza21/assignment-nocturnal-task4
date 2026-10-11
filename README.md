# Register reconciliation (Task 4)

Reads the handwritten goods receiving register (photos), the ERP goods-received notes and the
storekeeper's Excel, and tells the finance controller where the three disagree. Every row of every
source ends in exactly one outcome, and a person reviews only the doubtful ones.

## How it works

1. **Read the photos** (`recon/ocr.py`). Gemini turns each page into rows. Smudged or crossed-out
   cells come back as flags, never as guesses. Results are cached per page, keyed by the photo's hash.
2. **Clean** (`recon/clean.py`). Dates, supplier names, units and GRN numbers are put in one format.
   Raw files are only read, never changed, so running again cannot clean anything twice.
3. **Match** (`recon/match.py`). Rows are grouped by GRN number and compared on date, supplier, item,
   lot, quantity and unit. Outcomes: `MATCHED`, `MISMATCH` (field and each source's value), `MISSING`
   (which source), `DUPLICATE`, `NO_GRN`.
4. **Tie-out** (`recon/tieout.py`). Row counts and quantity totals are read from the raw inputs and
   compared with the outcomes. If anything does not tie, the run stops before writing anything.
5. **Review** (`recon/review.py`). `output/review.xlsx` lists only the doubtful rows, worst first,
   with the three sources side by side and the disagreeing cell coloured.
6. **Report** (`recon/report.py`). `output/report.html` walks through steps 1 to 5 in plain words for this run.
7. **Summary** (`recon/notify.py`). A short email: verdict, counts, top 3, the rest in the attachment.

## Run it

```
pip install -r requirements.txt
python run.py                 # cached pages, writes everything to output/
python run.py --send          # also emails the summary
python -m pytest
```

Settings go in a `.env` file (see `.env.example`). It is in `.gitignore` and never committed:
- `GEMINI_API_KEY` - only needed for a page that has not been read before (free key from Google AI Studio).
  `GEMINI_MODEL` overrides the default `gemini-3.8-flash`.
- `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO` - for `--send`. Use a Gmail app password.
  Without them the email is still saved as `output/summary.eml`.

Review: fill in the `decision` column (`ACCEPT_REGISTER`, `ACCEPT_ERP`, `ACCEPT_SHEET`,
`IGNORE`, `ESCALATE`), add a note, then run `python run.py` again. Decisions are applied at the
start of every run. Resolved rows stay resolved on later runs. If the underlying values change,
the row goes back to `PENDING`.

Monthly run: drop the new page photos in `data/raw/register/`. Known photos are skipped, only new ones
are read.

## Assumptions

- The register is the record of what physically arrived; the ERP and sheet are checked against it.
- Register dates are day/month, the year comes from the page header. Text dates in the sheet are month/day/year.
- 1 yard = 0.9144 m, applied before comparing quantities.
- Supplier names are matched by keyword (`Qasr`, `Taraz`, ...). An unknown supplier stays as written and shows as a mismatch.
- Where two sources agree and one differs, the odd one is suggested as wrong. This is a hint, not a decision.
- The sheet's second `4409` row is treated as a duplicate. A duplicate with different values would go to review.
- A row with no GRN (the 27 Sep return of 5,000 polybags) cannot be matched, so a person decides.
- An ERP entry made more than 2 days after the receipt date is flagged.

## How it fails, and how you would know

Each check is there so a bad reading never becomes a finance number. The run says what happened, and the last good output stays in place.

- **Unreadable cell:** the cell is flagged, the quantity is left blank, and that GRN goes to the review file for a person to decide (GRN 4428).
- **OCR:** a missing key, a bad answer, or a network error is printed in plain words. The page is checked before it is cached, so a broken reading is refused and the previous cache stays.
- **Tie-out:** row counts and quantity totals are proved against the raw inputs before any output file is replaced. The source that does not balance is named.
- **Review decision:** only `ACCEPT_REGISTER`, `ACCEPT_ERP`, `ACCEPT_SHEET`, `IGNORE`, and `ESCALATE` are applied. Any other value is reported by row and that row stays pending.
- **Email:** the summary is always written to `output/summary.eml`. If Gmail cannot send it, the reason is printed and the file is still there for the controller.

## Data handling

Only the supplied Kestrel files are used. `data/raw/` is never modified. `output/clean/` holds the cleaned
rows, `output/outcomes.csv` maps every source row to its outcome, `output/tieout.csv` holds the proof.
`data/extracted/` holds Gemini's reading of the two register photos. I compared it with a manual reading and they agree except for one cell: the item on GRN 4419, which Gemini read as H202 (zero). The three-way match flags it. A new page is read fresh each time, and Gemini can read the same handwriting differently on another run.

## With another week

- Crop each cell and show it next to the flagged value in the review file.
- Per-cell confidence from the OCR instead of flags only, and a second OCR pass to compare.
- Fuzzy supplier and item matching, and matching on lot when a GRN number is misread.
- Letter O and digit 0 look the same in this handwriting (see GRN 4408 and 4419). Flag O/0 doubt in item and lot fields at the OCR step, or check item names against a list of known materials.
- Deploy it properly: a hosted job with its own environment, secrets kept out of the repo, and a scheduler that runs the reconciliation once a month when the new register photos are in.
- Send urgent bugs to a dedicated Slack channel, or by email to the engineering team, the same day a run fails.
- Move the summary to WhatsApp (see below).
- A small web page for the review step.

## Next phase: the summary on WhatsApp (Twilio)

Not built yet. The message text already exists in `notify.build_body`, so only the sending changes.

1. Create a free Twilio account and open Messaging, then Try it out, then Send a WhatsApp message.
2. Each director sends `join <sandbox-code>` from their phone to the sandbox number shown there.
3. Add `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` (`whatsapp:` + sandbox number) and `WHATSAPP_TO` to `.env`.
4. Send with one request: `POST https://api.twilio.com/2010-04-01/Accounts/<sid>/Messages.json`, basic auth with the sid and token, form fields `From`, `To` (`whatsapp:+92...`) and `Body`.
5. Keep the body short (top 3 items) and share the review file as a link, not an attachment.
6. For real use, register an approved WhatsApp sender in Twilio. Messages sent outside the 24 hour reply window need an approved template.

## AI tools used

- **Claude:** initial planning and research.
- **Cursor:** mainly the code.
- **Gemini:** the OCR that reads the register photos.

I defined the architecture and took the technical decisions: the pipeline from photo to review, the match rules, the tie-out gate, and which libraries to use. Claude and Cursor carried out the planning and the coding under those decisions.
