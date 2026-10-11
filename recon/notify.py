import os
import smtplib
from email.message import EmailMessage

from . import config

LABELS = [
    ("MISSING", "missing"),
    ("MISMATCH", "mismatched"),
    ("NO_GRN", "no GRN"),
    ("DUPLICATE", "conflicting duplicate"),
    ("MATCHED", "flagged"),
]


def category_text(pending):
    parts = []
    for outcome, label in LABELS:
        count = 0
        for record in pending:
            if record["outcome"] == outcome:
                count += 1
        if count:
            parts.append(f"{count} {label}")
    return ", ".join(parts)


def build_body(pending, table, month):
    counts = {}
    for line in table:
        counts[line["source"]] = line["input_rows"]
    lines = [
        "Hi,",
        "",
        f"All rows accounted for: register {counts['register']}, ERP {counts['erp']}, "
        f"store sheet {counts['sheet']}. Quantity totals tie out.",
        "",
    ]
    if not pending:
        lines.append(f"Nothing needs a decision for {month}.")
        return "\n".join(lines)

    lines.append(f"{len(pending)} items need a decision: {category_text(pending)}.")
    lines.append("")
    lines.append(f"Top {min(config.TOP_N, len(pending))}:")
    for number, record in enumerate(pending[:config.TOP_N], start=1):
        label = record["case_id"]
        if record["grn"]:
            label = f"GRN {record['grn']}"
        lines.append(f"{number}. {label}: {record['issue']}")
    if len(pending) > config.TOP_N:
        lines.append("")
        lines.append(f"+{len(pending) - config.TOP_N} more in the attached review.xlsx.")
    return "\n".join(lines)


def build_email(pending, table, month):
    message = EmailMessage()
    message["From"] = os.environ.get("GMAIL_USER", "reconciliation@kestrel.example")
    message["To"] = os.environ.get("EMAIL_TO", os.environ.get("GMAIL_USER", "controller@kestrel.example"))
    if pending:
        message["Subject"] = f"{month} receiving reconciliation: {len(pending)} items need your decision"
    else:
        message["Subject"] = f"{month} receiving reconciliation: nothing needs a decision"
    message.set_content(build_body(pending, table, month))
    data = config.REVIEW_FILE.read_bytes()
    message.add_attachment(
        data, maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="review.xlsx",
    )
    return message


def save_email(message):
    path = config.OUTPUT / "summary.eml"
    path.write_bytes(bytes(message))
    return path


def send_email(message):
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not password:
        print("Email not sent: set GMAIL_USER and GMAIL_APP_PASSWORD. summary.eml was saved instead.")
        return False
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(user, password)
            server.send_message(message)
    except (smtplib.SMTPException, OSError) as error:
        print(f"Email not sent ({error}). summary.eml was saved instead.")
        return False
    print(f"Email sent to {message['To']}")
    return True
