import uuid

from flows import tool


@tool
def generate_unique_id() -> str:
    """
    Generate an 8-digit unique value.

    Returns:
        str: An 8-digit unique value.
    """
    # Generate a unique ID using uuid
    unique_id = str(uuid.uuid4())
    # Take the first 8 characters to create an 8-digit unique value
    eight_digit_unique_value = unique_id[:8]

    return eight_digit_unique_value
