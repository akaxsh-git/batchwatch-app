"""In-app notifications, plus optional email if SMTP settings are in .env.

SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD (e.g. a Gmail App Password),
NOTIFY_EMAIL_TO. If they are not set, only in-app notifications are created.
"""
import os
import smtplib
from email.message import EmailMessage

from .audit import now
from .db import session


def notify(recipient, org, verdict, ref, message):
    with session() as con:
        con.execute("""INSERT INTO notifications(recipient, org, message, verdict, ref, created_at)
                       VALUES (?,?,?,?,?,?)""", (recipient, org, message, verdict, ref, now()))
    send_email(f"BatchWatch: {verdict}", message)


def send_email(subject, body) -> bool:
    host, to = os.getenv("SMTP_HOST"), os.getenv("NOTIFY_EMAIL_TO")
    if not host or not to:
        return False
    try:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, os.getenv("SMTP_USER"), to
        msg.set_content(body)
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            s.send_message(msg)
        return True
    except Exception:
        return False


def for_actor(actor) -> list:
    with session() as con:
        if actor["role"] == "pharmacist":
            q, p = "SELECT * FROM notifications WHERE org=? ORDER BY id DESC", (actor["org"],)
        elif actor["role"] == "household":
            q, p = "SELECT * FROM notifications WHERE recipient=? ORDER BY id DESC", (actor["name"],)
        else:
            q, p = "SELECT * FROM notifications ORDER BY id DESC LIMIT 50", ()
        return [dict(r) for r in con.execute(q, p)]


def mark_read(actor, ids):
    with session() as con:
        for i in ids:
            con.execute("UPDATE notifications SET read=1 WHERE id=?", (i,))
