def can_delete_group(user_email: str, group: dict) -> bool:
    return group["created_by"] == user_email


def can_delete_event(user_email: str, event: dict) -> bool:
    return event["created_by"] == user_email


def can_delete_expense(user_email: str, expense: dict) -> bool:
    return expense["created_by"] == user_email or expense["paid_by"] == user_email


def can_edit_expense(user_email: str, expense: dict) -> bool:
    return expense["created_by"] == user_email or expense["paid_by"] == user_email
