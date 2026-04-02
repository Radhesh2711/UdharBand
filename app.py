import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = Path(__file__).parent / "groups.json"

# Data shape:
# {
#   "Group Name": {
#     "members": ["A", "B", "C"],
#     "events": {
#       "Event Name": [
#         {"description": "...", "amount": 100, "paid_by": "A", "shares": {"B": 50, "C": 50}}
#       ]
#     }
#   }
# }


def load_data():
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text())
    return {}


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2))


def migrate_group(grp):
    """Migrate old formats to new {members, events} shape."""
    if isinstance(grp, list):
        return {"members": grp, "events": {}}
    if "expenses" in grp and "events" not in grp:
        # Old format: flat expenses list -> put them under a "Default" event
        events = {}
        if grp["expenses"]:
            events["Default"] = grp["expenses"]
        return {"members": grp.get("members", []), "events": events}
    grp.setdefault("members", [])
    grp.setdefault("events", {})
    return grp


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


# ── App ───────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="UdharBand", layout="centered")
st.title("UdharBand")

data = load_data()

# Migrate all groups on load
for g in list(data.keys()):
    data[g] = migrate_group(data[g])
save_data(data)

# Steps: home | add_members | events | expenses
init_state("step", "home")
init_state("current_group", None)
init_state("current_event", None)

# ── Sidebar ───────────────────────────────────────────────────────────────────

existing_groups = list(data.keys())
if existing_groups:
    st.sidebar.header("Existing Groups")
    for g in existing_groups:
        grp = data[g]
        n_members = len(grp["members"])
        n_events = len(grp["events"])
        col1, col2 = st.sidebar.columns([3, 1])
        if col1.button(f"{g}  ({n_members} members, {n_events} events)", key=f"load_{g}", use_container_width=True):
            st.session_state["current_group"] = g
            st.session_state["current_event"] = None
            st.session_state["step"] = "events"
            st.rerun()
        if col2.button("X", key=f"del_{g}"):
            del data[g]
            save_data(data)
            if st.session_state.get("current_group") == g:
                st.session_state["step"] = "home"
                st.session_state["current_group"] = None
                st.session_state["current_event"] = None
            st.rerun()
    st.sidebar.divider()

if st.sidebar.button("+ New Group"):
    st.session_state["step"] = "home"
    st.session_state["current_group"] = None
    st.session_state["current_event"] = None
    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: Create group
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "home":
    st.header("Create a New Group")
    name = st.text_input("Group name", placeholder="e.g. Goa Trip, Flatmates")
    if st.button("Next →"):
        if not name.strip():
            st.error("Please enter a group name.")
        elif name.strip() in data:
            st.error("A group with this name already exists.")
        else:
            gname = name.strip()
            data[gname] = {"members": [], "events": {}}
            save_data(data)
            st.session_state["current_group"] = gname
            st.session_state["step"] = "add_members"
            st.rerun()
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Add members
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "add_members":
    gname = st.session_state["current_group"]
    group = data[gname]
    members = group["members"]

    st.header(f"Add Members to '{gname}'")

    if members:
        st.write("**Current members:**")
        for i, m in enumerate(members):
            c1, c2 = st.columns([5, 1])
            c1.write(f"{i+1}. {m}")
            if c2.button("Remove", key=f"rm_{i}"):
                members.pop(i)
                save_data(data)
                st.rerun()

    new_name = st.text_input("Member name", placeholder="Enter a name", key="member_input")
    col_add, col_done = st.columns(2)

    with col_add:
        if st.button("Add Member", use_container_width=True):
            if not new_name.strip():
                st.error("Enter a name.")
            elif new_name.strip() in members:
                st.error(f"'{new_name.strip()}' is already added.")
            else:
                members.append(new_name.strip())
                save_data(data)
                st.rerun()

    with col_done:
        if st.button("Done Adding Members →", use_container_width=True, type="primary"):
            if len(members) < 2:
                st.error("Add at least 2 members.")
            else:
                st.session_state["step"] = "events"
                st.rerun()

    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Events list
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "events":
    gname = st.session_state["current_group"]
    group = data[gname]
    members = group["members"]
    events = group["events"]

    st.header(f"{gname}")
    st.caption(f"Members: {', '.join(members)}")

    st.subheader("Events")

    # Create new event
    col1, col2 = st.columns([3, 1])
    with col1:
        new_event = st.text_input("New event name", placeholder="e.g. March Expenses, Goa Day 1", label_visibility="collapsed")
    with col2:
        if st.button("Add Event", use_container_width=True):
            if not new_event.strip():
                st.error("Enter an event name.")
            elif new_event.strip() in events:
                st.error("Event already exists in this group.")
            else:
                events[new_event.strip()] = []
                save_data(data)
                st.session_state["current_event"] = new_event.strip()
                st.session_state["step"] = "expenses"
                st.rerun()

    # List existing events
    if events:
        for ev_name in events:
            exps = events[ev_name]
            total = sum(e["amount"] for e in exps)
            col_name, col_del = st.columns([4, 1])
            if col_name.button(
                f"{ev_name}  —  {len(exps)} expenses, total: ${total:.2f}",
                key=f"ev_{ev_name}", use_container_width=True
            ):
                st.session_state["current_event"] = ev_name
                st.session_state["step"] = "expenses"
                st.rerun()
            if col_del.button("X", key=f"del_ev_{ev_name}"):
                del events[ev_name]
                save_data(data)
                st.rerun()
    else:
        st.info("No events yet. Create one above.")

    st.divider()
    if st.button("← Edit Members"):
        st.session_state["step"] = "add_members"
        st.rerun()

    st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4: Expenses within an event
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state["step"] == "expenses":
    gname = st.session_state["current_group"]
    ev_name = st.session_state["current_event"]

    # Guard: if event is missing or None, go back to events list
    if not ev_name or ev_name not in data.get(gname, {}).get("events", {}):
        st.session_state["step"] = "events"
        st.session_state["current_event"] = None
        st.rerun()

    group = data[gname]
    members = group["members"]
    expenses = group["events"][ev_name]

    st.header(f"{gname} / {ev_name}")
    st.caption(f"Members: {', '.join(members)}")

    if st.button("← Back to Events"):
        st.session_state["current_event"] = None
        st.session_state["step"] = "events"
        st.rerun()

    # ── Who Owes Who table ────────────────────────────────────────────────────

    if expenses:
        st.subheader("Who Owes Who")
        owes_df = build_owes_table(members, expenses)
        st.markdown("*Rows owe to columns*")
        st.dataframe(owes_df, use_container_width=True)
        st.divider()

    # ── Add Expense ───────────────────────────────────────────────────────────

    st.subheader("Add Expense")

    if "exp_counter" not in st.session_state:
        st.session_state["exp_counter"] = 0
    k = st.session_state["exp_counter"]

    desc = st.text_input("Expense description", placeholder="e.g. Dinner, Taxi, Hotel", key=f"exp_desc_{k}")
    amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f", key=f"exp_amount_{k}")

    st.write("**Who paid?**")
    paid_by = st.radio("Paid by", members, horizontal=True, label_visibility="collapsed", key=f"exp_paid_{k}")

    st.write("**Who is part of this expense?**")
    involved = []
    inv_cols = st.columns(min(len(members), 4))
    for i, m in enumerate(members):
        with inv_cols[i % min(len(members), 4)]:
            if st.checkbox(m, value=True, key=f"inv_{k}_{m}"):
                involved.append(m)

    split_type = st.radio("How to split?", ["Equal", "Percentage", "Ratio"], horizontal=True, key=f"exp_split_{k}")

    split_inputs = {}
    if split_type == "Percentage" and involved:
        st.caption("Enter percentage for each involved member (must total 100%):")
        pcols = st.columns(min(len(involved), 4))
        for i, m in enumerate(involved):
            with pcols[i % min(len(involved), 4)]:
                split_inputs[m] = st.number_input(
                    m, min_value=0.0, max_value=100.0, step=0.01,
                    format="%.2f", key=f"pct_{k}_{m}"
                )
    elif split_type == "Ratio" and involved:
        st.caption("Enter ratio for each involved member:")
        rcols = st.columns(min(len(involved), 4))
        for i, m in enumerate(involved):
            with rcols[i % min(len(involved), 4)]:
                split_inputs[m] = st.number_input(
                    m, min_value=0.0, step=0.1,
                    format="%.1f", key=f"rat_{k}_{m}"
                )

    if st.button("Add Expense", type="primary"):
        if not desc.strip():
            st.error("Enter a description.")
        elif not involved:
            st.error("Select at least one person involved.")
        elif split_type == "Equal":
            share = round(amount / len(involved), 2)
            shares = {p: share for p in involved}
            diff = round(amount - sum(shares.values()), 2)
            if diff != 0:
                shares[involved[0]] = round(shares[involved[0]] + diff, 2)
            expenses.append({
                "description": desc.strip(), "amount": amount,
                "paid_by": paid_by, "shares": shares,
            })
            save_data(data)
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
                expenses.append({
                    "description": desc.strip(), "amount": amount,
                    "paid_by": paid_by, "shares": shares,
                })
                save_data(data)
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
                expenses.append({
                    "description": desc.strip(), "amount": amount,
                    "paid_by": paid_by, "shares": shares,
                })
                save_data(data)
                st.session_state["exp_counter"] += 1
                st.rerun()

    # ── Expense History ───────────────────────────────────────────────────────

    if expenses:
        st.divider()
        st.subheader("Expense History")
        editing_idx = st.session_state.get("editing_expense")

        for i, exp in enumerate(expenses):
            is_editing = editing_idx == i

            with st.expander(
                f"**{exp['description']}** — {exp['amount']:.2f} (paid by {exp['paid_by']})",
                expanded=is_editing,
            ):
                if not is_editing:
                    split_data = []
                    for person, share in exp["shares"].items():
                        owes_to_payer = share if person != exp["paid_by"] else 0
                        split_data.append({
                            "Person": person,
                            "Share": f"{share:.2f}",
                            "Owes to " + exp["paid_by"]: f"{owes_to_payer:.2f}" if owes_to_payer > 0 else "-",
                        })
                    st.table(pd.DataFrame(split_data).set_index("Person"))
                    btn_edit, btn_del, _ = st.columns([1, 1, 3])
                    if btn_edit.button("Edit", key=f"edit_{i}"):
                        st.session_state["editing_expense"] = i
                        st.rerun()
                    if btn_del.button("Delete", key=f"del_{i}"):
                        expenses.pop(i)
                        save_data(data)
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
                    paid_idx = members.index(exp["paid_by"]) if exp["paid_by"] in members else 0
                    ed_paid = st.radio(
                        "Paid by", members, index=paid_idx, horizontal=True,
                        label_visibility="collapsed", key=f"ed_paid_{i}"
                    )

                    st.write("**Who is part of this expense?**")
                    ed_involved = []
                    ed_inv_cols = st.columns(min(len(members), 4))
                    for mi, m in enumerate(members):
                        with ed_inv_cols[mi % min(len(members), 4)]:
                            checked = m in exp["shares"]
                            if st.checkbox(m, value=checked, key=f"ed_inv_{i}_{m}"):
                                ed_involved.append(m)

                    ed_split = st.radio(
                        "How to split?", ["Equal", "Percentage", "Ratio"],
                        horizontal=True, key=f"ed_split_{i}"
                    )

                    ed_split_inputs = {}
                    if ed_split == "Percentage" and ed_involved:
                        st.caption("Enter percentage for each involved member (must total 100%):")
                        epcols = st.columns(min(len(ed_involved), 4))
                        for mi, m in enumerate(ed_involved):
                            with epcols[mi % min(len(ed_involved), 4)]:
                                ed_split_inputs[m] = st.number_input(
                                    m, min_value=0.0, max_value=100.0, step=0.01,
                                    format="%.2f", key=f"ed_pct_{i}_{m}"
                                )
                    elif ed_split == "Ratio" and ed_involved:
                        st.caption("Enter ratio for each involved member:")
                        ercols = st.columns(min(len(ed_involved), 4))
                        for mi, m in enumerate(ed_involved):
                            with ercols[mi % min(len(ed_involved), 4)]:
                                ed_split_inputs[m] = st.number_input(
                                    m, min_value=0.0, step=0.1,
                                    format="%.1f", key=f"ed_rat_{i}_{m}"
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
                                expenses[i] = {
                                    "description": ed_desc.strip(),
                                    "amount": ed_amount,
                                    "paid_by": ed_paid,
                                    "shares": shares,
                                }
                                save_data(data)
                                st.session_state.pop("editing_expense", None)
                                st.rerun()

                    with btn_cancel:
                        if st.button("Cancel", key=f"cancel_{i}"):
                            st.session_state.pop("editing_expense", None)
                            st.rerun()

    # ── Simplify Expenses ─────────────────────────────────────────────────────

    if expenses:
        st.divider()
        if st.button("Simplify Expenses", type="primary", use_container_width=True):
            st.session_state["show_simplified"] = True

        if st.session_state.get("show_simplified"):
            settlements = simplify_debts(members, expenses)
            st.subheader("Simplified Settlements")
            if settlements:
                for debtor, creditor, amt in settlements:
                    st.markdown(f"**{debtor}** owes **{creditor}** **${amt:.2f}**")
            else:
                st.success("All settled up! No one owes anything.")
