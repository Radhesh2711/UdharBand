import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ── Users ────────────────────────────────────────────────────────────────────


def ensure_user(email: str, display_name: str | None = None) -> None:
    sb = get_client()
    name = display_name or email.split("@")[0]
    sb.table("users").upsert(
        {"email": email, "display_name": name},
        on_conflict="email",
    ).execute()


def get_user_display_names(emails: list[str]) -> dict[str, str]:
    if not emails:
        return {}
    sb = get_client()
    resp = sb.table("users").select("email, display_name").in_("email", emails).execute()
    return {r["email"]: r["display_name"] or r["email"].split("@")[0] for r in resp.data}


# ── Groups ───────────────────────────────────────────────────────────────────


def create_group(name: str, created_by: str) -> dict:
    sb = get_client()
    resp = sb.table("groups").insert(
        {"name": name, "created_by": created_by}
    ).execute()
    group = resp.data[0]
    # Auto-add creator as member
    sb.table("group_members").insert(
        {"group_id": group["id"], "user_email": created_by}
    ).execute()
    return group


def get_user_groups(email: str) -> list[dict]:
    sb = get_client()
    resp = (
        sb.table("group_members")
        .select("group_id, groups(id, name, created_by, created_at)")
        .eq("user_email", email)
        .execute()
    )
    groups = []
    for row in resp.data:
        g = row["groups"]
        if g:
            groups.append(g)
    return groups


def get_group(group_id: str) -> dict | None:
    sb = get_client()
    resp = sb.table("groups").select("id, name, created_by").eq("id", group_id).execute()
    return resp.data[0] if resp.data else None


def delete_group(group_id: str) -> None:
    sb = get_client()
    sb.table("groups").delete().eq("id", group_id).execute()


# ── Members ──────────────────────────────────────────────────────────────────


def get_group_members(group_id: str) -> list[dict]:
    sb = get_client()
    resp = (
        sb.table("group_members")
        .select("user_email, users(email, display_name)")
        .eq("group_id", group_id)
        .execute()
    )
    members = []
    for row in resp.data:
        u = row["users"]
        members.append({
            "email": u["email"],
            "display_name": u["display_name"] or u["email"].split("@")[0],
        })
    return members


def add_member(group_id: str, email: str, display_name: str | None = None) -> None:
    sb = get_client()
    # Ensure user row exists
    ensure_user(email, display_name)
    sb.table("group_members").upsert(
        {"group_id": group_id, "user_email": email},
        on_conflict="group_id,user_email",
    ).execute()


def remove_member(group_id: str, email: str) -> None:
    sb = get_client()
    sb.table("group_members").delete().eq("group_id", group_id).eq("user_email", email).execute()


# ── Events ───────────────────────────────────────────────────────────────────


def create_event(group_id: str, name: str, created_by: str) -> dict:
    sb = get_client()
    resp = sb.table("events").insert(
        {"group_id": group_id, "name": name, "created_by": created_by}
    ).execute()
    return resp.data[0]


def get_events(group_id: str) -> list[dict]:
    sb = get_client()
    resp = (
        sb.table("events")
        .select("id, group_id, name, created_by, created_at")
        .eq("group_id", group_id)
        .order("created_at")
        .execute()
    )
    return resp.data


def get_events_with_totals(group_id: str) -> list[dict]:
    """Get events with expense totals in 2 queries instead of N+1."""
    sb = get_client()
    events_resp = (
        sb.table("events")
        .select("id, group_id, name, created_by, created_at")
        .eq("group_id", group_id)
        .order("created_at")
        .execute()
    )
    events = events_resp.data
    if not events:
        return events

    event_ids = [e["id"] for e in events]
    expenses_resp = (
        sb.table("expenses")
        .select("event_id, amount")
        .in_("event_id", event_ids)
        .execute()
    )

    totals = {}
    for exp in expenses_resp.data:
        eid = exp["event_id"]
        totals[eid] = totals.get(eid, 0) + float(exp["amount"])

    for ev in events:
        ev["total"] = round(totals.get(ev["id"], 0), 2)

    return events


def delete_event(event_id: str) -> None:
    sb = get_client()
    sb.table("events").delete().eq("id", event_id).execute()


# ── Expenses ─────────────────────────────────────────────────────────────────


def create_expense(
    event_id: str,
    description: str,
    amount: float,
    paid_by: str,
    created_by: str,
    shares: dict[str, float],
) -> dict:
    sb = get_client()
    resp = sb.table("expenses").insert({
        "event_id": event_id,
        "description": description,
        "amount": amount,
        "paid_by": paid_by,
        "created_by": created_by,
    }).execute()
    expense = resp.data[0]

    share_rows = [
        {"expense_id": expense["id"], "user_email": email, "share_amount": amt}
        for email, amt in shares.items()
    ]
    if share_rows:
        sb.table("expense_shares").insert(share_rows).execute()

    expense["shares"] = shares
    return expense


def get_expenses(event_id: str) -> list[dict]:
    sb = get_client()
    resp = (
        sb.table("expenses")
        .select("id, event_id, description, amount, paid_by, created_by, created_at, expense_shares(user_email, share_amount)")
        .eq("event_id", event_id)
        .order("created_at")
        .execute()
    )
    expenses = []
    for row in resp.data:
        shares = {s["user_email"]: float(s["share_amount"]) for s in row.get("expense_shares", [])}
        expenses.append({
            "id": row["id"],
            "description": row["description"],
            "amount": float(row["amount"]),
            "paid_by": row["paid_by"],
            "created_by": row["created_by"],
            "shares": shares,
        })
    return expenses


def update_expense(
    expense_id: str,
    description: str,
    amount: float,
    paid_by: str,
    shares: dict[str, float],
) -> None:
    sb = get_client()
    sb.table("expenses").update({
        "description": description,
        "amount": amount,
        "paid_by": paid_by,
    }).eq("id", expense_id).execute()

    # Replace shares: delete old, insert new
    sb.table("expense_shares").delete().eq("expense_id", expense_id).execute()
    share_rows = [
        {"expense_id": expense_id, "user_email": email, "share_amount": amt}
        for email, amt in shares.items()
    ]
    if share_rows:
        sb.table("expense_shares").insert(share_rows).execute()


def delete_expense(expense_id: str) -> None:
    sb = get_client()
    sb.table("expenses").delete().eq("id", expense_id).execute()
