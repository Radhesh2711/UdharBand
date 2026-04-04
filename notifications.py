import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlencode

import streamlit as st

APP_URL = "https://udharband.streamlit.app"


def _app_link(group_id: str = None, event_id: str = None) -> str:
    params = {}
    if group_id:
        params["group"] = group_id
    if event_id:
        params["event"] = event_id
    if params:
        return f"{APP_URL}?{urlencode(params)}"
    return APP_URL


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


def notify_added_to_group(member_email: str, group_name: str, added_by: str, group_id: str):
    """Notify a person they were added to a group."""
    link = _app_link(group_id=group_id)
    _send_email(
        member_email,
        f"UdharBand: You were added to '{group_name}'",
        f"""
        <p>Hi! Welcome to UdharBand.</p>
        <p><strong>{added_by}</strong> added you to a group <strong>{group_name}</strong>. Use this email <strong>{member_email}</strong> to sign in with Google.</p>
        <p>Hope you enjoy the experience.</p>
        <p><a href="{link}">Open {group_name} →</a></p>
        <p>UdharBand</p>
        """,
    )


def notify_group_deleted(member_emails: list[str], group_name: str, deleted_by: str,
                         event_settlements: list[dict], display_map: dict):
    """Notify all group members when a group is deleted, with per-event settlement snapshots.

    event_settlements: [{"name": "Event Name", "settlements": [(debtor_email, creditor_email, amt), ...]}]
    display_map: {email: display_name}
    """
    def _dn(email):
        return display_map.get(email, email.split("@")[0])

    for recipient in member_emails:
        if recipient == deleted_by:
            continue

        # Calculate total owed/owe for this recipient across all events
        total_owed_to_me = 0.0  # others owe me
        total_i_owe = 0.0       # I owe others
        for ev in event_settlements:
            for debtor, creditor, amt in ev["settlements"]:
                if creditor == recipient:
                    total_owed_to_me += amt
                elif debtor == recipient:
                    total_i_owe += amt

        # Summary line
        if total_owed_to_me > 0.01 or total_i_owe > 0.01:
            summary_parts = []
            if total_owed_to_me > 0.01:
                summary_parts.append(f"You are owed <strong>${total_owed_to_me:.2f}</strong>")
            if total_i_owe > 0.01:
                summary_parts.append(f"You owe <strong>${total_i_owe:.2f}</strong>")
            summary_html = f"<p><strong>Your total:</strong> {' and '.join(summary_parts)}.</p>"
        else:
            summary_html = "<p>You are settled for this group. No debts, no credits.</p>"

        # Per-event breakdown (only settlements involving this recipient)
        events_html = ""
        for ev in event_settlements:
            my_settlements = [
                (d, c, a) for d, c, a in ev["settlements"]
                if d == recipient or c == recipient
            ]
            events_html += f"<h3 style='margin: 1rem 0 0.3rem 0;'>{ev['name']}</h3>"
            if my_settlements:
                rows = ""
                for debtor, creditor, amt in my_settlements:
                    rows += f"<tr><td style='padding:4px 12px;'>{_dn(creditor)}</td><td style='padding:4px 12px;'>{_dn(debtor)}</td><td style='padding:4px 12px;'>${amt:.2f}</td></tr>"
                events_html += f"""
                <table style="border-collapse: collapse; margin: 0.3rem 0;">
                    <tr style="border-bottom: 1px solid #555;">
                        <th style="padding:4px 12px; text-align:left;">Creditor</th>
                        <th style="padding:4px 12px; text-align:left;">Debtor</th>
                        <th style="padding:4px 12px; text-align:left;">Amount</th>
                    </tr>
                    {rows}
                </table>"""
            else:
                events_html += "<p style='color: #888;'>No settlements for you in this event.</p>"

        _send_email(
            recipient,
            f"UdharBand: Group '{group_name}' has been deleted",
            f"""
            <p>Hi again.</p>
            <p><strong>{_dn(deleted_by)}</strong> deleted the group <strong>{group_name}</strong>.</p>
            {summary_html}
            <p><strong>Settlement breakdown by event:</strong></p>
            {events_html}
            <p>Hope to see you again.</p>
            <p>UdharBand.</p>
            """,
        )


def notify_removed_from_group(member_email: str, group_name: str):
    """Notify a person they were removed from a group."""
    _send_email(
        member_email,
        f"UdharBand: You were removed from '{group_name}'",
        f"""
        <p>Hi!</p>
        <p>You have been removed from the group <strong>{group_name}</strong>.</p>
        <p>Sorry to see you go. Looking forward to serving you again!</p>
        <p>UdharBand</p>
        """,
    )


def notify_event_created(member_emails: list[str], group_name: str, event_name: str,
                         created_by: str, group_id: str, event_id: str):
    """Notify all group members when an event is created."""
    link = _app_link(group_id=group_id, event_id=event_id)
    recipients = [e for e in member_emails if e != created_by]
    _send_to_many(
        recipients,
        f"UdharBand: New event '{event_name}' in '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{created_by}</strong> created a new event <strong>{event_name}</strong> in the group <strong>{group_name}</strong>.</p>
        <p><a href="{link}">Open {event_name} →</a></p>
        """,
    )


def notify_expense_added(shares: dict[str, float], group_name: str, event_name: str,
                         description: str, amount: float, paid_by_name: str, added_by: str,
                         group_id: str, event_id: str):
    """Notify people included in an expense (except the one who added it)."""
    link = _app_link(group_id=group_id, event_id=event_id)
    for email, share in shares.items():
        if email == added_by:
            continue
        _send_email(
            email,
            f"UdharBand: New expense in '{group_name} / {event_name}'",
            f"""
            <p>Hi!</p>
            <p>A new expense was added in <strong>{group_name} / {event_name}</strong>:</p>
            <ul>
                <li><strong>Description:</strong> {description}</li>
                <li><strong>Amount:</strong> ${amount:.2f}</li>
                <li><strong>Paid by:</strong> {paid_by_name}</li>
                <li><strong>Your share:</strong> ${share:.2f}</li>
                <li><strong>Added by:</strong> {added_by}</li>
            </ul>
            <p><a href="{link}">Open {event_name} →</a></p>
            """,
        )


def notify_event_deleted(member_emails: list[str], group_name: str, event_name: str,
                         deleted_by: str, group_id: str):
    """Notify all group members when an event is deleted."""
    link = _app_link(group_id=group_id)
    recipients = [e for e in member_emails if e != deleted_by]
    _send_to_many(
        recipients,
        f"UdharBand: Event '{event_name}' deleted from '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{deleted_by}</strong> deleted the event <strong>{event_name}</strong> from the group <strong>{group_name}</strong>.</p>
        <p><a href="{link}">Open {group_name} →</a></p>
        """,
    )


def notify_event_edited(member_emails: list[str], group_name: str, event_name: str,
                         edited_by: str, group_id: str, event_id: str):
    """Notify all group members when an event is edited."""
    link = _app_link(group_id=group_id, event_id=event_id)
    recipients = [e for e in member_emails if e != edited_by]
    _send_to_many(
        recipients,
        f"UdharBand: Event '{event_name}' edited in '{group_name}'",
        f"""
        <p>Hi!</p>
        <p><strong>{edited_by}</strong> edited the event <strong>{event_name}</strong> in the group <strong>{group_name}</strong>.</p>
        <p><a href="{link}">Open {event_name} →</a></p>
        """,
    )


def notify_expense_edited(involved_emails: list[str], group_name: str, event_name: str,
                          description: str, amount: float, edited_by: str,
                          group_id: str, event_id: str):
    """Notify people involved in an expense when it's edited."""
    link = _app_link(group_id=group_id, event_id=event_id)
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
        <p><a href="{link}">Open {event_name} →</a></p>
        """,
    )


def notify_expense_deleted(involved_emails: list[str], group_name: str, event_name: str,
                           description: str, amount: float, deleted_by: str,
                           group_id: str, event_id: str):
    """Notify people involved in an expense when it's deleted."""
    link = _app_link(group_id=group_id, event_id=event_id)
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
        <p><a href="{link}">Open {event_name} →</a></p>
        """,
    )
