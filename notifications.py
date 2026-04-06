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

        # Calculate net balance for this recipient across all events
        # Positive = others owe me, negative = I owe others
        balances = {}  # {other_email: net_amount}
        for ev in event_settlements:
            for debtor, creditor, amt in ev["settlements"]:
                if creditor == recipient:
                    balances[debtor] = balances.get(debtor, 0) + amt
                elif debtor == recipient:
                    balances[creditor] = balances.get(creditor, 0) - amt

        # Summary line
        owe_lines = []
        owed_lines = []
        for person, net in balances.items():
            if net < -0.01:
                owe_lines.append(f"You owe <strong>{_dn(person)}</strong> <strong>${-net:.2f}</strong>")
            elif net > 0.01:
                owed_lines.append(f"<strong>{_dn(person)}</strong> owes you <strong>${net:.2f}</strong>")

        if owe_lines or owed_lines:
            summary_html = "<p><strong>Your total:</strong></p><ul>"
            for line in owe_lines + owed_lines:
                summary_html += f"<li>{line}</li>"
            summary_html += "</ul>"
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
                events_html += "<p style='color: #888;'>You are all settled for this event 😉</p>"

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
                         deleted_by: str, group_id: str, settlements: list[tuple] = None,
                         display_map: dict = None, expenses: list[dict] = None):
    """Notify all group members when an event is deleted, with personalized settlement and transaction history."""
    link = _app_link(group_id=group_id)
    settlements = settlements or []
    display_map = display_map or {}
    expenses = expenses or []

    def _dn(email):
        return display_map.get(email, email.split("@")[0])

    for recipient in member_emails:
        if recipient == deleted_by:
            continue

        # Find settlements involving this recipient
        my_settlements = [(d, c, a) for d, c, a in settlements if d == recipient or c == recipient]

        if my_settlements:
            balances = {}
            for debtor, creditor, amt in my_settlements:
                if creditor == recipient:
                    balances[debtor] = balances.get(debtor, 0) + amt
                elif debtor == recipient:
                    balances[creditor] = balances.get(creditor, 0) - amt

            summary_lines = []
            for person, net in balances.items():
                if net < -0.01:
                    summary_lines.append(f"You owe <strong>{_dn(person)}</strong> <strong>${-net:.2f}</strong>")
                elif net > 0.01:
                    summary_lines.append(f"<strong>{_dn(person)}</strong> owes you <strong>${net:.2f}</strong>")

            if summary_lines:
                settlement_html = "<p><strong>Last settlement snapshot:</strong></p><ul>"
                for line in summary_lines:
                    settlement_html += f"<li>{line}</li>"
                settlement_html += "</ul>"
            else:
                settlement_html = "<p>You are all settled for this event 😉</p>"
        else:
            settlement_html = "<p>You are all settled for this event 😉</p>"

        # Transaction history — expenses this recipient was part of
        my_expenses = [e for e in expenses if recipient in e.get("shares", {})]
        if my_expenses:
            tx_rows = ""
            for exp in my_expenses:
                share = exp["shares"].get(recipient, 0)
                tx_rows += f"""<tr>
                    <td style='padding:4px 12px;'>{exp['description']}</td>
                    <td style='padding:4px 12px;'>${exp['amount']:.2f}</td>
                    <td style='padding:4px 12px;'>{_dn(exp['paid_by'])}</td>
                    <td style='padding:4px 12px;'>${share:.2f}</td>
                </tr>"""
            tx_html = f"""
            <p><strong>Your transaction history:</strong></p>
            <table style="border-collapse: collapse; margin: 0.3rem 0;">
                <tr style="border-bottom: 1px solid #555;">
                    <th style="padding:4px 12px; text-align:left;">Description</th>
                    <th style="padding:4px 12px; text-align:left;">Total</th>
                    <th style="padding:4px 12px; text-align:left;">Paid by</th>
                    <th style="padding:4px 12px; text-align:left;">Your share</th>
                </tr>
                {tx_rows}
            </table>"""
        else:
            tx_html = ""

        _send_email(
            recipient,
            f"UdharBand: Event '{event_name}' deleted from '{group_name}'",
            f"""
            <p>Hi!</p>
            <p><strong>{_dn(deleted_by)}</strong> deleted the event <strong>{event_name}</strong> from the group <strong>{group_name}</strong>.</p>
            {settlement_html}
            {tx_html}
            <p><a href="{link}">Open {group_name} →</a></p>
            <p>UdharBand.</p>
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


def notify_expense_edited(new_shares: dict[str, float], old_shares: dict[str, float],
                          group_name: str, event_name: str,
                          new_description: str, old_description: str,
                          new_amount: float, old_amount: float,
                          paid_by_name: str, edited_by: str,
                          group_id: str, event_id: str):
    """Notify people involved in an expense when it's edited, with personalized details."""
    link = _app_link(group_id=group_id, event_id=event_id)
    all_involved = set(list(new_shares.keys()) + list(old_shares.keys()))

    for email in all_involved:
        if email == edited_by:
            continue

        was_in = email in old_shares
        now_in = email in new_shares
        share = new_shares.get(email, 0)

        # Build change details
        changes = ""
        if old_description != new_description:
            changes += f"<li>The expense was described as <strong>{new_description}</strong></li>"
        if abs(old_amount - new_amount) > 0.01:
            changes += f"<li>The amount was changed to <strong>${new_amount:.2f}</strong></li>"

        if was_in and not now_in:
            # Removed from expense
            _send_email(
                email,
                f"UdharBand: Expense edited in '{group_name} / {event_name}'",
                f"""
                <p>Hi!</p>
                <p><strong>{edited_by}</strong> edited the expense <strong>{old_description}</strong>.</p>
                {f'<ul>{changes}</ul>' if changes else ''}
                <p>You were removed from expense <strong>{new_description}</strong> in <strong>{event_name}</strong> for group <strong>{group_name}</strong>.</p>
                <p><strong>Your share:</strong> $0.00</p>
                <p><a href="{link}">Open {event_name} →</a></p>
                <p>UdharBand.</p>
                """,
            )
        else:
            # Still in or newly added
            _send_email(
                email,
                f"UdharBand: Expense edited in '{group_name} / {event_name}'",
                f"""
                <p>Hi!</p>
                <p><strong>{edited_by}</strong> edited the expense <strong>{old_description}</strong>.</p>
                {f'<ul>{changes}</ul>' if changes else ''}
                <ul>
                    <li><strong>Description:</strong> {new_description}</li>
                    <li><strong>Amount:</strong> ${new_amount:.2f}</li>
                    <li><strong>Paid by:</strong> {paid_by_name}</li>
                    <li><strong>Your share:</strong> ${share:.2f}</li>
                </ul>
                <p><a href="{link}">Open {event_name} →</a></p>
                <p>UdharBand.</p>
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


# ── Settlement notifications ─────────────────────────────────────────────────


def notify_debtor_settled(creditor_email: str, debtor_name: str, amount: float,
                          event_name: str, group_name: str, group_id: str, event_id: str):
    """Notify creditor that debtor claims to have settled."""
    link = _app_link(group_id=group_id, event_id=event_id)
    _send_email(
        creditor_email,
        f"UdharBand: {debtor_name} has settled with you",
        f"""
        <p>Hi!</p>
        <p><strong>{debtor_name}</strong> has settled your share of <strong>${amount:.2f}</strong> for <strong>{event_name}</strong> under <strong>{group_name}</strong>.</p>
        <p>If received, don't forget to approve on UdharBand.</p>
        <p><a href="{link}">Open {event_name} →</a></p>
        <p>UdharBand.</p>
        """,
    )


def notify_creditor_approved(debtor_email: str, creditor_name: str, amount: float,
                              event_name: str, group_name: str, group_id: str, event_id: str):
    """Notify debtor that creditor approved the settlement."""
    link = _app_link(group_id=group_id, event_id=event_id)
    _send_email(
        debtor_email,
        f"UdharBand: {creditor_name} approved your settlement",
        f"""
        <p>Hi!</p>
        <p><strong>{creditor_name}</strong> approves of your settlement of <strong>${amount:.2f}</strong> for <strong>{event_name}</strong> under <strong>{group_name}</strong>.</p>
        <p>You are amazing! 🤩</p>
        <p><a href="{link}">Open {event_name} →</a></p>
        <p>UdharBand.</p>
        """,
    )


def notify_creditor_settled_directly(debtor_email: str, creditor_name: str, amount: float,
                                      event_name: str, group_name: str, group_id: str, event_id: str):
    """Notify debtor that creditor has directly confirmed settlement."""
    link = _app_link(group_id=group_id, event_id=event_id)
    _send_email(
        debtor_email,
        f"UdharBand: {creditor_name} confirmed your settlement",
        f"""
        <p>Hi!</p>
        <p><strong>{creditor_name}</strong> approves of your settlement of <strong>${amount:.2f}</strong> for <strong>{event_name}</strong> under <strong>{group_name}</strong>.</p>
        <p>You are amazing! 🤩</p>
        <p><a href="{link}">Open {event_name} →</a></p>
        <p>UdharBand.</p>
        """,
    )
