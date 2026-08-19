from rest_framework.exceptions import ValidationError

ALLOWED_TRANSITIONS = {
    'PENDING_PAYMENT': {'PAID', 'CANCELLED'},
    'PAID': {'RECEIVED'},
    'RECEIVED': {'PREPARING'},
    'PREPARING': {'READY'},
    'READY': {'COMPLETED'},
    'COMPLETED': set(),
    'CANCELLED': set(),
}

NEXT_STAFF_STATUS = {
    'PAID': 'RECEIVED',
    'RECEIVED': 'PREPARING',
    'PREPARING': 'READY',
    'READY': 'COMPLETED',
}


def validate_status_transition(current_status, new_status):
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot move order from {current_status} to {new_status}."
        )