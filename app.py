from collections import defaultdict

import pandas as pd
import streamlit as st

import db
from auth import require_login, build_display_map
from permissions import can_delete_group, can_delete_event, can_delete_expense, can_edit_expense
import notifications

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.set_page_config(page_title="UdharBand", layout="centered", page_icon="💸")

CUSTOM_CSS = """
<style>
/* ── Global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body {
    font-family: 'Inter', sans-serif;
}

/* ── Cards ── */
.card {
    background: linear-gradient(135deg, #1E1E30 0%, #252542 100%);
    border: 1px solid rgba(108, 92, 231, 0.2);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.8rem;
    transition: all 0.2s ease;
}
.card:hover {
    border-color: rgba(108, 92, 231, 0.5);
    box-shadow: 0 4px 20px rgba(108, 92, 231, 0.1);
}

/* ── Settlement cards ── */
.settlement-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid rgba(108, 92, 231, 0.3);
    border-radius: 16px;
    padding: 1rem 1.5rem;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.settlement-arrow {
    color: #6C5CE7;
    font-size: 1.4rem;
    margin: 0 0.8rem;
}
.settlement-name {
    font-weight: 600;
    font-size: 1rem;
    color: #E8E8F0;
}
.settlement-amount {
    background: linear-gradient(135deg, #6C5CE7, #a29bfe);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    font-size: 1.2rem;
}
.settled-card {
    background: linear-gradient(135deg, #1a2e1a 0%, #163e2e 100%);
    border: 1px solid rgba(0, 206, 158, 0.3);
    border-radius: 16px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    color: #00ce9e;
    font-weight: 600;
    font-size: 1.1rem;
}

/* ── Expense cards ── */
.expense-card {
    background: linear-gradient(135deg, #1E1E30 0%, #252542 100%);
    border: 1px solid rgba(108, 92, 231, 0.15);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.expense-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.3rem;
}
.expense-desc {
    font-weight: 600;
    font-size: 1rem;
    color: #E8E8F0;
}
.expense-amount {
    font-weight: 700;
    font-size: 1.1rem;
    color: #a29bfe;
}
.expense-meta {
    color: #8888aa;
    font-size: 0.85rem;
}

/* ── Member chips ── */
.member-chip {
    display: inline-block;
    background: rgba(108, 92, 231, 0.15);
    border: 1px solid rgba(108, 92, 231, 0.3);
    border-radius: 20px;
    padding: 0.3rem 0.8rem;
    margin: 0.2rem 0.3rem 0.2rem 0;
    font-size: 0.85rem;
    color: #a29bfe;
    font-weight: 500;
}

/* ── Event cards ── */
.event-card {
    background: linear-gradient(135deg, #1E1E30 0%, #252542 100%);
    border: 1px solid rgba(108, 92, 231, 0.2);
    border-radius: 16px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
}
.event-name {
    font-weight: 600;
    font-size: 1.05rem;
    color: #E8E8F0;
}
.event-meta {
    color: #8888aa;
    font-size: 0.85rem;
    margin-top: 0.2rem;
}

/* ── Page header ── */
.page-title {
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6C5CE7, #a29bfe, #fd79a8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.page-subtitle {
    color: #8888aa;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

/* ── Section header ── */
.section-header {
    font-size: 1.3rem;
    font-weight: 600;
    color: #E8E8F0;
    margin: 1.5rem 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid rgba(108, 92, 231, 0.3);
}

/* ── Hide sidebar ── */
section[data-testid="stSidebar"] { display: none; }
button[data-testid="collapsedControl"] { display: none; }

/* ── Footer ── */
.app-footer {
    position: fixed;
    bottom: 1rem;
    left: 0;
    width: 100%;
    text-align: center;
    z-index: 100;
    pointer-events: none;
}
.footer-email {
    color: #8888aa;
    font-size: 0.8rem;
}

/* ── Button overrides ── */
.stButton > button[kind="primary"] {
    border-radius: 12px;
    font-weight: 600;
}
.stButton > button[kind="secondary"] {
    border-radius: 12px;
}
.stButton > button {
    border-radius: 12px;
}

/* ── Input overrides ── */
.stTextInput > div > div > input {
    border-radius: 12px;
}
.stNumberInput > div > div > input {
    border-radius: 12px;
}
.stSelectbox > div > div {
    border-radius: 12px;
}

/* ── Share table in expense detail ── */
.share-row {
    display: grid;
    grid-template-columns: 1fr 100px 80px;
    gap: 0 1rem;
    align-items: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(108, 92, 231, 0.1);
    font-size: 0.9rem;
}
.share-row:last-child {
    border-bottom: none;
}
.share-person { color: #E8E8F0; font-weight: 500; }
.share-amount { color: #a29bfe; font-weight: 600; text-align: right; }
.share-status { font-weight: 500; text-align: right; }
.share-status.owes { color: #fd79a8; }
.share-status.paid { color: #00ce9e; }

/* Vertically align columns */
div[data-testid="stHorizontalBlock"] {
    align-items: center;
}


</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────


def build_owes_table(members, expenses):
    owes = defaultdict(lambda: defaultdict(float))
    for exp in expenses:
        paid_by = exp["paid_by"]
        for person, share in exp["shares"].items():
            if person != paid_by:
                owes[person][paid_by] += share

    net = defaultdict(lambda: defaultdict(float))
    for a in members:
        for b in members:
            if a != b:
                diff = owes[a][b] - owes[b][a]
                if diff > 0.01:
                    net[a][b] = round(diff, 2)

    rows = []
    for debtor in members:
        row = {"Member": debtor}
        for creditor in members:
            if debtor == creditor:
                row[creditor] = "-"
            else:
                amt = net[debtor].get(creditor, 0)
                row[creditor] = f"{amt:.2f}" if amt > 0.01 else "-"
        rows.append(row)
    return pd.DataFrame(rows).set_index("Member")


def simplify_debts(members, expenses):
    balance = defaultdict(float)
    for exp in expenses:
        paid_by = exp["paid_by"]
        for person, share in exp["shares"].items():
            if person != paid_by:
                balance[paid_by] += share
                balance[person] -= share

    creditors = []
    debtors = []
    for person in members:
        bal = round(balance.get(person, 0), 2)
        if bal > 0.01:
            creditors.append([person, bal])
        elif bal < -0.01:
            debtors.append([person, -bal])

    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])

    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        amt = round(min(debtors[i][1], creditors[j][1]), 2)
        if amt > 0.01:
            settlements.append((debtors[i][0], creditors[j][0], amt))
        debtors[i][1] = round(debtors[i][1] - amt, 2)
        creditors[j][1] = round(creditors[j][1] - amt, 2)
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return settlements


def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def dn(email, display_map):
    """Short helper: display name for an email."""
    return display_map.get(email, email.split("@")[0])


CHIP_COLORS = [
    ("#6C5CE7", "rgba(108, 92, 231, 0.15)"),   # purple
    ("#00cec9", "rgba(0, 206, 201, 0.15)"),     # teal
    ("#fd79a8", "rgba(253, 121, 168, 0.15)"),   # pink
    ("#fdcb6e", "rgba(253, 203, 110, 0.15)"),   # yellow
    ("#55efc4", "rgba(85, 239, 196, 0.15)"),    # green
    ("#74b9ff", "rgba(116, 185, 255, 0.15)"),   # blue
    ("#e17055", "rgba(225, 112, 85, 0.15)"),    # orange
    ("#dfe6e9", "rgba(223, 230, 233, 0.15)"),   # grey
]

def render_member_chips(emails, display_map):
    """Render members as styled chips with different colors."""
    chips = ""
    for i, e in enumerate(emails):
        color, bg = CHIP_COLORS[i % len(CHIP_COLORS)]
        chips += f'<span style="display:inline-block;border:1px solid {color};background:{bg};border-radius:20px;padding:0.3rem 0.8rem;margin:0.2rem 0.3rem;font-size:0.85rem;color:{color};font-weight:500;">{dn(e, display_map)}</span>'
    st.markdown(f'<div style="text-align: center;">{chips}</div>', unsafe_allow_html=True)




def render_settlement_card(debtor_name, creditor_name, amount):
    st.markdown(f"""
    <div class="settlement-card">
        <span class="settlement-name">{debtor_name}</span>
        <span class="settlement-arrow">→</span>
        <span class="settlement-name">{creditor_name}</span>
        <span class="settlement-amount">${amount:.2f}</span>
    </div>
    """, unsafe_allow_html=True)


def render_expense_card(description, amount, paid_by_name):
    st.markdown(f"""
    <div class="expense-card">
        <div class="expense-header">
            <span class="expense-desc">{description}</span>
            <span class="expense-amount">${amount:.2f}</span>
        </div>
        <div class="expense-meta">Paid by {paid_by_name}</div>
    </div>
    """, unsafe_allow_html=True)


# ── App ───────────────────────────────────────────────────────────────────────

user_email = require_login()

st.markdown('<div class="page-title" style="text-align: center; margin-bottom: 1.5rem;">UdharBand</div>', unsafe_allow_html=True)

# Footer: logged-in status + logout (rendered at bottom via CSS)
footer_html = f"""
<div class="app-footer">
    <span class="footer-email">Logged in as {user_email}</span>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)

# Logout button in a hidden-ish bottom area — we'll render it at the very end
# Store reference so we can render logout at bottom of each page
def render_logout():
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_logout, _ = st.columns([2, 1, 2])
    with col_logout:
        if st.button("Logout", type="secondary", use_container_width=True):
            st.logout()

# Steps: home | add_members | events | expenses
init_state("step", "home")
init_state("current_group", None)   # group UUID
init_state("current_event", None)   # event UUID

# Deep-link via query params (e.g. ?group=UUID&event=UUID)
qp = st.query_params
if "group" in qp and st.session_state.get("_deep_link_handled") != qp.get("group", "") + qp.get("event", ""):
    st.session_state["current_group"] = qp["group"]
    if "event" in qp:
        st.session_state["current_event"] = qp["event"]
        st.session_state["step"] = "expenses"
    else:
        st.session_state["step"] = "events"
    st.session_state["_deep_link_handled"] = qp.get("group", "") + qp.get("event", "")
    st.query_params.clear()

# ═══════════════════════════════════════════════════════════════════════════════
# HOME: Group list
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "home":
    user_groups = db.get_user_groups(user_email)

    st.markdown('<div style="text-align: center; font-size: 1.3rem; font-weight: 600; color: #E8E8F0; margin: 1.5rem 0 1rem 0;">Your Groups</div>', unsafe_allow_html=True)

    if user_groups:
        for g in user_groups:
            n_events = len(db.get_events(g["id"]))
            _, col_center, _ = st.columns([1, 3, 1])
            with col_center:
                if st.button(f"{g['name']}  ·  {n_events} events", key=f"load_{g['id']}", use_container_width=True):
                    st.session_state["current_group"] = g["id"]
                    st.session_state["current_event"] = None
                    st.session_state["step"] = "events"
                    st.rerun()
    else:
        st.markdown("""
        <div class="card" style="text-align: center; color: #8888aa;">
            No groups yet. Create one below!
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_create, _ = st.columns([1, 3, 1])
    with col_create:
        if st.button("+ Create New Group", type="primary", use_container_width=True):
            st.session_state["step"] = "create_group"
            st.rerun()
    render_logout()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# CREATE GROUP
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "create_group":
    st.markdown('<div class="section-header">Create a New Group</div>', unsafe_allow_html=True)
    name = st.text_input("Group name", placeholder="e.g. Goa Trip, Flatmates")
    if st.button("Next →", type="primary"):
        if not name.strip():
            st.error("Please enter a group name.")
        else:
            group = db.create_group(name.strip(), user_email)
            st.session_state["current_group"] = group["id"]
            st.session_state["step"] = "add_members"
            st.rerun()
    render_logout()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Add members
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "add_members":
    group_id = st.session_state["current_group"]
    members = db.get_group_members(group_id)
    display_map = build_display_map(members)
    member_emails = [m["email"] for m in members]

    # Get group name for header
    groups = db.get_user_groups(user_email)
    group_name = next((g["name"] for g in groups if g["id"] == group_id), "Group")

    st.markdown(f'<div class="section-header">Add Members to \'{group_name}\'</div>', unsafe_allow_html=True)

    if members:
        for i, m in enumerate(members):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"""
            <div class="card" style="padding: 0.6rem 1rem; margin-bottom: 0.4rem;">
                <span style="font-weight: 600; color: #E8E8F0;">{m['display_name']}</span>
                <span style="color: #8888aa; font-size: 0.85rem; margin-left: 0.5rem;">{m['email']}</span>
            </div>
            """, unsafe_allow_html=True)
            if m["email"] != user_email or len(members) > 1:
                if c2.button("Remove", key=f"rm_{m['email']}"):
                    db.remove_member(group_id, m["email"])
                    st.rerun()

    if "member_counter" not in st.session_state:
        st.session_state["member_counter"] = 0
    mk = st.session_state["member_counter"]

    st.markdown("<br>", unsafe_allow_html=True)
    col_name, col_email = st.columns(2)
    with col_name:
        new_name = st.text_input("Name", placeholder="Enter their name", key=f"member_name_{mk}")
    with col_email:
        new_email = st.text_input("Email", placeholder="Enter their email address", key=f"member_email_{mk}")
    col_add, col_done = st.columns(2)

    with col_add:
        if st.button("Add Member", use_container_width=True):
            email = new_email.strip().lower()
            name = new_name.strip()
            if not email:
                st.error("Enter an email.")
            elif "@" not in email:
                st.error("Please enter a valid email address.")
            elif email in member_emails:
                st.error(f"'{email}' is already a member.")
            else:
                db.add_member(group_id, email, name if name else None)
                notifications.notify_added_to_group(email, group_name, user_email, group_id)
                st.session_state["member_counter"] += 1
                st.rerun()

    with col_done:
        if st.button("Done Adding Members →", use_container_width=True, type="primary"):
            if len(members) < 2:
                st.error("Add at least 2 members.")
            else:
                st.session_state["step"] = "events"
                st.rerun()

    render_logout()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Events list
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "events":
    group_id = st.session_state["current_group"]
    members = db.get_group_members(group_id)
    display_map = build_display_map(members)
    member_emails = [m["email"] for m in members]
    events = db.get_events(group_id)

    # Get group name
    groups = db.get_user_groups(user_email)
    group_name = next((g["name"] for g in groups if g["id"] == group_id), "Group")

    st.markdown(f'<div style="text-align: center; font-size: 1.3rem; font-weight: 600; color: #E8E8F0; margin: 1.5rem 0 1.2rem 0;">{group_name}</div>', unsafe_allow_html=True)
    render_member_chips(member_emails, display_map)

    st.markdown('<div style="text-align: center; font-size: 1.1rem; font-weight: 600; color: #a29bfe; margin: 2.5rem 0 0.8rem 0;">Events</div>', unsafe_allow_html=True)

    # List existing events
    if events:
        for ev in events:
            ev_expenses = db.get_expenses(ev["id"])
            total = sum(e["amount"] for e in ev_expenses)
            _, col_center, _ = st.columns([1, 3, 1])
            with col_center:
                if st.button(f"{ev['name']}  ·  ${total:.2f}", key=f"ev_{ev['id']}", use_container_width=True):
                    st.session_state["current_event"] = ev["id"]
                    st.session_state["step"] = "expenses"
                    st.rerun()
    else:
        st.markdown("""
        <div class="card" style="text-align: center; color: #8888aa;">
            No events yet. Create one below.
        </div>
        """, unsafe_allow_html=True)

    # Create new event
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col1:
        new_event = st.text_input("New event name", placeholder="e.g. March Expenses, Goa Day 1", label_visibility="collapsed")
    with col2:
        if st.button("Add Event", use_container_width=True, type="primary"):
            if not new_event.strip():
                st.error("Enter an event name.")
            else:
                event_names = [ev["name"] for ev in events]
                if new_event.strip() in event_names:
                    st.error("Event already exists in this group.")
                else:
                    ev = db.create_event(group_id, new_event.strip(), user_email)
                    notifications.notify_event_created(member_emails, group_name, new_event.strip(), user_email, group_id, ev["id"])
                    st.session_state["current_event"] = ev["id"]
                    st.session_state["step"] = "expenses"
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    group_data = next((g for g in groups if g["id"] == group_id), None)
    show_delete = group_data and can_delete_group(user_email, group_data)
    if show_delete:
        col_back, col_edit, col_delgrp = st.columns(3)
    else:
        col_back, col_edit = st.columns(2)
    with col_back:
        if st.button("← My Groups", use_container_width=True):
            st.session_state["step"] = "home"
            st.session_state["current_group"] = None
            st.session_state["current_event"] = None
            st.rerun()
    with col_edit:
        if st.button("Edit Members", key="edit_members", use_container_width=True, type="primary"):
            st.session_state["step"] = "add_members"
            st.rerun()
    if show_delete:
        with col_delgrp:
            if st.button("Delete Group", key="del_group", use_container_width=True, icon=":material/delete:"):
                db.delete_group(group_id)
                st.session_state["step"] = "home"
                st.session_state["current_group"] = None
                st.session_state["current_event"] = None
                st.rerun()

    render_logout()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Expenses within an event
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "expenses":
    group_id = st.session_state["current_group"]
    event_id = st.session_state["current_event"]

    if not event_id:
        st.session_state["step"] = "events"
        st.session_state["current_event"] = None
        st.rerun()

    members = db.get_group_members(group_id)
    display_map = build_display_map(members)
    member_emails = [m["email"] for m in members]
    expenses = db.get_expenses(event_id)

    # Get group and event names
    groups = db.get_user_groups(user_email)
    group_name = next((g["name"] for g in groups if g["id"] == group_id), "Group")
    events = db.get_events(group_id)
    event_name = next((ev["name"] for ev in events if ev["id"] == event_id), "Event")

    st.markdown(f'<div class="section-header">{group_name} / {event_name}</div>', unsafe_allow_html=True)
    render_member_chips(member_emails, display_map)

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_del_ev = st.columns(2)
    with col_back:
        if st.button("← Back to Events", use_container_width=True):
            st.session_state["current_event"] = None
            st.session_state["step"] = "events"
            st.rerun()
    with col_del_ev:
        current_event_data = next((ev for ev in events if ev["id"] == event_id), None)
        if current_event_data and can_delete_event(user_email, current_event_data):
            if st.button("Delete Event", key="del_event", use_container_width=True, icon=":material/delete:"):
                notifications.notify_event_deleted(member_emails, group_name, event_name, user_email, group_id)
                db.delete_event(event_id)
                st.session_state["current_event"] = None
                st.session_state["step"] = "events"
                st.rerun()

    # ── Add Expense ───────────────────────────────────────────────────────────

    st.markdown('<div class="section-header">Add Expense</div>', unsafe_allow_html=True)

    if "exp_counter" not in st.session_state:
        st.session_state["exp_counter"] = 0
    k = st.session_state["exp_counter"]

    desc = st.text_input("Expense description", placeholder="e.g. Dinner, Taxi, Hotel", key=f"exp_desc_{k}")
    amount_str = st.text_input("Amount", placeholder="e.g. 150.00", key=f"exp_amount_{k}")

    st.write("**Who paid?**")
    display_names_list = [dn(e, display_map) for e in member_emails]
    paid_idx = st.radio("Paid by", range(len(member_emails)),
                        format_func=lambda i: display_names_list[i],
                        horizontal=True, label_visibility="collapsed", key=f"exp_paid_{k}")
    paid_by = member_emails[paid_idx]

    st.write("**Who is part of this expense?**")
    involved = []
    inv_cols = st.columns(min(len(member_emails), 4))
    for i, email in enumerate(member_emails):
        with inv_cols[i % min(len(member_emails), 4)]:
            if st.checkbox(dn(email, display_map), value=True, key=f"inv_{k}_{email}"):
                involved.append(email)

    split_type = st.radio("How to split?", ["Equal", "Percentage", "Ratio"], horizontal=True, key=f"exp_split_{k}")

    split_inputs = {}
    if split_type == "Percentage" and involved:
        st.caption("Enter percentage for each involved member (must total 100%):")
        pcols = st.columns(min(len(involved), 4))
        for i, email in enumerate(involved):
            with pcols[i % min(len(involved), 4)]:
                split_inputs[email] = st.number_input(
                    dn(email, display_map), min_value=0.0, max_value=100.0, step=0.01,
                    format="%.2f", key=f"pct_{k}_{email}"
                )
    elif split_type == "Ratio" and involved:
        st.caption("Enter ratio for each involved member:")
        rcols = st.columns(min(len(involved), 4))
        for i, email in enumerate(involved):
            with rcols[i % min(len(involved), 4)]:
                split_inputs[email] = st.number_input(
                    dn(email, display_map), min_value=0.0, step=0.1,
                    format="%.1f", key=f"rat_{k}_{email}"
                )

    if st.button("Add Expense", type="primary", use_container_width=True):
        if not desc.strip():
            st.error("Enter a description.")
        elif not amount_str.strip():
            st.error("Enter an amount.")
        else:
            try:
                amount = round(float(amount_str.strip()), 2)
                if amount <= 0:
                    raise ValueError()
            except ValueError:
                amount = None
                st.error("Enter a valid positive number for amount.")
        if not desc.strip() or not amount_str.strip() or amount is None:
            pass
        elif not involved:
            st.error("Select at least one person involved.")
        elif split_type == "Equal":
            share = round(amount / len(involved), 2)
            shares = {p: share for p in involved}
            diff = round(amount - sum(shares.values()), 2)
            if diff != 0:
                shares[involved[0]] = round(shares[involved[0]] + diff, 2)
            db.create_expense(event_id, desc.strip(), amount, paid_by, user_email, shares)
            notifications.notify_expense_added(shares, group_name, event_name, desc.strip(), amount, dn(paid_by, display_map), user_email, group_id, event_id)
            st.session_state["exp_counter"] += 1
            st.rerun()
        elif split_type == "Percentage":
            pcts = {m: split_inputs.get(m, 0) for m in involved}
            total_pct = round(sum(pcts.values()), 2)
            if abs(total_pct - 100.0) > 0.01:
                st.error(f"Percentages sum to {total_pct}%. Must be 100%.")
            else:
                shares = {p: round(amount * v / 100, 2) for p, v in pcts.items() if v > 0}
                diff = round(amount - sum(shares.values()), 2)
                if diff != 0 and shares:
                    first = next(iter(shares))
                    shares[first] = round(shares[first] + diff, 2)
                db.create_expense(event_id, desc.strip(), amount, paid_by, user_email, shares)
                notifications.notify_expense_added(shares, group_name, event_name, desc.strip(), amount, dn(paid_by, display_map), user_email, group_id, event_id)
                st.session_state["exp_counter"] += 1
                st.rerun()
        elif split_type == "Ratio":
            ratios = {m: split_inputs.get(m, 0) for m in involved}
            total_ratio = sum(ratios.values())
            if total_ratio == 0:
                st.error("Ratios can't all be zero.")
            else:
                shares = {p: round(amount * v / total_ratio, 2) for p, v in ratios.items() if v > 0}
                diff = round(amount - sum(shares.values()), 2)
                if diff != 0 and shares:
                    first = next(iter(shares))
                    shares[first] = round(shares[first] + diff, 2)
                db.create_expense(event_id, desc.strip(), amount, paid_by, user_email, shares)
                notifications.notify_expense_added(shares, group_name, event_name, desc.strip(), amount, dn(paid_by, display_map), user_email, group_id, event_id)
                st.session_state["exp_counter"] += 1
                st.rerun()

    # ── Expense History ───────────────────────────────────────────────────────

    if expenses:
        st.markdown('<div class="section-header">Expense History</div>', unsafe_allow_html=True)
        editing_idx = st.session_state.get("editing_expense")

        for i, exp in enumerate(expenses):
            is_editing = editing_idx == i

            label = f"{exp['description']} — ${exp['amount']:.2f} · paid by {dn(exp['paid_by'], display_map)}"
            with st.expander(label, expanded=is_editing):
                if not is_editing:
                    # Styled share breakdown
                    share_html = ""
                    for person, share in exp["shares"].items():
                        owes = share if person != exp["paid_by"] else 0
                        owes_tag = '<span class="share-status owes">owes</span>' if owes > 0 else '<span class="share-status paid">paid</span>'
                        share_html += f"""
                        <div class="share-row">
                            <span class="share-person">{dn(person, display_map)}</span>
                            <span class="share-amount">${share:.2f}</span>
                            {owes_tag}
                        </div>"""
                    st.markdown(f'<div class="card">{share_html}</div>', unsafe_allow_html=True)

                    btn_cols = st.columns([1, 1, 3])
                    if can_edit_expense(user_email, exp):
                        with btn_cols[0]:
                            if st.button("Edit", key=f"edit_{i}", use_container_width=True, icon=":material/edit:"):
                                st.session_state["editing_expense"] = i
                                st.rerun()
                    if can_delete_expense(user_email, exp):
                        with btn_cols[1]:
                            del_clicked = st.button("Delete", key=f"del_{i}", use_container_width=True, icon=":material/delete:")
                            if del_clicked:
                                notifications.notify_expense_deleted(list(exp["shares"].keys()), group_name, event_name, exp["description"], exp["amount"], user_email, group_id, event_id)
                                db.delete_expense(exp["id"])
                                if editing_idx is not None and editing_idx >= i:
                                    st.session_state.pop("editing_expense", None)
                                st.rerun()
                else:
                    ed_desc = st.text_input(
                        "Description", value=exp["description"], key=f"ed_desc_{i}"
                    )
                    ed_amount = st.number_input(
                        "Amount", min_value=0.01, step=0.01, format="%.2f",
                        value=float(exp["amount"]), key=f"ed_amount_{i}"
                    )

                    st.write("**Who paid?**")
                    paid_idx_edit = member_emails.index(exp["paid_by"]) if exp["paid_by"] in member_emails else 0
                    ed_paid_idx = st.radio(
                        "Paid by", range(len(member_emails)),
                        index=paid_idx_edit,
                        format_func=lambda idx: display_names_list[idx],
                        horizontal=True,
                        label_visibility="collapsed", key=f"ed_paid_{i}"
                    )
                    ed_paid = member_emails[ed_paid_idx]

                    st.write("**Who is part of this expense?**")
                    ed_involved = []
                    ed_inv_cols = st.columns(min(len(member_emails), 4))
                    for mi, email in enumerate(member_emails):
                        with ed_inv_cols[mi % min(len(member_emails), 4)]:
                            checked = email in exp["shares"]
                            if st.checkbox(dn(email, display_map), value=checked, key=f"ed_inv_{i}_{email}"):
                                ed_involved.append(email)

                    ed_split = st.radio(
                        "How to split?", ["Equal", "Percentage", "Ratio"],
                        horizontal=True, key=f"ed_split_{i}"
                    )

                    ed_split_inputs = {}
                    if ed_split == "Percentage" and ed_involved:
                        st.caption("Enter percentage for each involved member (must total 100%):")
                        epcols = st.columns(min(len(ed_involved), 4))
                        for mi, email in enumerate(ed_involved):
                            with epcols[mi % min(len(ed_involved), 4)]:
                                ed_split_inputs[email] = st.number_input(
                                    dn(email, display_map), min_value=0.0, max_value=100.0, step=0.01,
                                    format="%.2f", key=f"ed_pct_{i}_{email}"
                                )
                    elif ed_split == "Ratio" and ed_involved:
                        st.caption("Enter ratio for each involved member:")
                        ercols = st.columns(min(len(ed_involved), 4))
                        for mi, email in enumerate(ed_involved):
                            with ercols[mi % min(len(ed_involved), 4)]:
                                ed_split_inputs[email] = st.number_input(
                                    dn(email, display_map), min_value=0.0, step=0.1,
                                    format="%.1f", key=f"ed_rat_{i}_{email}"
                                )

                    btn_save, btn_cancel, _ = st.columns([1, 1, 3])

                    with btn_save:
                        if st.button("Save", key=f"save_{i}", type="primary"):
                            error = None
                            shares = {}
                            if not ed_desc.strip():
                                error = "Enter a description."
                            elif not ed_involved:
                                error = "Select at least one person involved."
                            elif ed_split == "Equal":
                                share = round(ed_amount / len(ed_involved), 2)
                                shares = {p: share for p in ed_involved}
                                diff = round(ed_amount - sum(shares.values()), 2)
                                if diff != 0:
                                    shares[ed_involved[0]] = round(shares[ed_involved[0]] + diff, 2)
                            elif ed_split == "Percentage":
                                pcts = {m: ed_split_inputs.get(m, 0) for m in ed_involved}
                                total_pct = round(sum(pcts.values()), 2)
                                if abs(total_pct - 100.0) > 0.01:
                                    error = f"Percentages sum to {total_pct}%. Must be 100%."
                                else:
                                    shares = {p: round(ed_amount * v / 100, 2) for p, v in pcts.items() if v > 0}
                                    diff = round(ed_amount - sum(shares.values()), 2)
                                    if diff != 0 and shares:
                                        first = next(iter(shares))
                                        shares[first] = round(shares[first] + diff, 2)
                            elif ed_split == "Ratio":
                                ratios = {m: ed_split_inputs.get(m, 0) for m in ed_involved}
                                total_ratio = sum(ratios.values())
                                if total_ratio == 0:
                                    error = "Ratios can't all be zero."
                                else:
                                    shares = {p: round(ed_amount * v / total_ratio, 2) for p, v in ratios.items() if v > 0}
                                    diff = round(ed_amount - sum(shares.values()), 2)
                                    if diff != 0 and shares:
                                        first = next(iter(shares))
                                        shares[first] = round(shares[first] + diff, 2)

                            if error:
                                st.error(error)
                            else:
                                db.update_expense(exp["id"], ed_desc.strip(), ed_amount, ed_paid, shares)
                                all_involved = set(list(shares.keys()) + list(exp["shares"].keys()))
                                notifications.notify_expense_edited(list(all_involved), group_name, event_name, ed_desc.strip(), ed_amount, user_email, group_id, event_id)
                                st.session_state.pop("editing_expense", None)
                                st.rerun()

                    with btn_cancel:
                        if st.button("Cancel", key=f"cancel_{i}"):
                            st.session_state.pop("editing_expense", None)
                            st.rerun()

    # ── Simplify Expenses ─────────────────────────────────────────────────────

    if expenses:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Simplify Expenses", type="primary", use_container_width=True):
            st.session_state["show_simplified"] = True

        if st.session_state.get("show_simplified"):
            settlements = simplify_debts(member_emails, expenses)
            st.markdown('<div class="section-header">Settlements</div>', unsafe_allow_html=True)
            if settlements:
                for debtor, creditor, amt in settlements:
                    render_settlement_card(
                        dn(debtor, display_map),
                        dn(creditor, display_map),
                        amt,
                    )
            else:
                st.markdown("""
                <div class="settled-card">
                    All settled up! No one owes anything.
                </div>
                """, unsafe_allow_html=True)

    render_logout()
