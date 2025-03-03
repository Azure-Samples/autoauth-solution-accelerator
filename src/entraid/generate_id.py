import uuid


def generate_unique_id() -> str:
    """
    Generate an 8-digit unique value.

    Returns:
        str: An 8-digit unique value.
    """
    unique_id = str(uuid.uuid4())
    eight_digit_unique_value = unique_id[:8]

    return eight_digit_unique_value
