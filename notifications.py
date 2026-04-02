import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import streamlit as st


def _get_smtp_config():
    try:
        return st.secrets["smtp"]["sender_email"], st.secrets["smtp"]["app_password"]
    except (KeyError, FileNotFoundError):
        return None, None


def _send_email(to: str, subject: str, body_html: str):
    """Send an email in a background thread so it doesn't block the UI."""
    sender, password = _get_smtp_config()
    if not sender or not password:
        return

    def _send():
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"UdharBand <{sender}>"
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body_html, "html"))

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
        except Exception:
            pass  # Silently fail — notifications are best-effort

    threading.Thread(target=_send, daemon=True).start()


def _send_to_many(recipients: list[str], subject: str, body_html: str):
    for email in recipients:
        _send_email(email, subject, body_html)


# ── Notification triggers ────────────────────────────────────────────────────


def notify_added_to_group(member_email: str, group_name: str, added_by: str):
    """Notify a person they were added to a group."""
    _send_email(
        member_email,
        f"UdharBand: You were added to '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{added_by}</strong> added you to the group <strong>{group_name}</strong> on UdharBand.</p>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )


def notify_event_created(member_emails: list[str], group_name: str, event_name: str, created_by: str):
    """Notify all group members when an event is created."""
    recipients = [e for e in member_emails if e != created_by]
    _send_to_many(
        recipients,
        f"UdharBand: New event '{event_name}' in '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{created_by}</strong> created a new event <strong>{event_name}</strong> in the group <strong>{group_name}</strong>.</p>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )


def notify_expense_added(involved_emails: list[str], group_name: str, event_name: str,
                         description: str, amount: float, paid_by_name: str, added_by: str):
    """Notify people included in an expense (except the one who added it)."""
    recipients = [e for e in involved_emails if e != added_by]
    _send_to_many(
        recipients,
        f"UdharBand: New expense in '{group_name} / {event_name}'",
        f"""
        <p>Hi!</p>
        <p>A new expense was added in <strong>{group_name} / {event_name}</strong>:</p>
        <ul>
            <li><strong>Description:</strong> {description}</li>
            <li><strong>Amount:</strong> ${amount:.2f}</li>
            <li><strong>Paid by:</strong> {paid_by_name}</li>
            <li><strong>Added by:</strong> {added_by}</li>
        </ul>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )


def notify_event_deleted(member_emails: list[str], group_name: str, event_name: str, deleted_by: str):
    """Notify all group members when an event is deleted."""
    recipients = [e for e in member_emails if e != deleted_by]
    _send_to_many(
        recipients,
        f"UdharBand: Event '{event_name}' deleted from '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{deleted_by}</strong> deleted the event <strong>{event_name}</strong> from the group <strong>{group_name}</strong>.</p>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )


def notify_event_edited(member_emails: list[str], group_name: str, event_name: str, edited_by: str):
    """Notify all group members when an event is edited."""
    recipients = [e for e in member_emails if e != edited_by]
    _send_to_many(
        recipients,
        f"UdharBand: Event '{event_name}' edited in '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{edited_by}</strong> edited the event <strong>{event_name}</strong> in the group <strong>{group_name}</strong>.</p>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )


def notify_expense_edited(involved_emails: list[str], group_name: str, event_name: str,
                          description: str, amount: float, edited_by: str):
    """Notify people involved in an expense when it's edited."""
    recipients = [e for e in involved_emails if e != edited_by]
    _send_to_many(
        recipients,
        f"UdharBand: Expense edited in '{group_name} / {event_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{edited_by}</strong> edited an expense in <strong>{group_name} / {event_name}</strong>:</p>
        <ul>
            <li><strong>Description:</strong> {description}</li>
            <li><strong>Amount:</strong> ${amount:.2f}</li>
        </ul>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )


def notify_expense_deleted(involved_emails: list[str], group_name: str, event_name: str,
                           description: str, amount: float, deleted_by: str):
    """Notify people involved in an expense when it's deleted."""
    recipients = [e for e in involved_emails if e != deleted_by]
    _send_to_many(
        recipients,
        f"UdharBand: Expense deleted from '{group_name} / {event_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{deleted_by}</strong> deleted an expense from <strong>{group_name} / {event_name}</strong>:</p>
        <ul>
            <li><strong>Description:</strong> {description}</li>
            <li><strong>Amount:</strong> ${amount:.2f}</li>
        </ul>
        <p>Open the app to view: <a href="https://udharband.streamlit.app">udharband.streamlit.app</a></p>
        """,
    )
