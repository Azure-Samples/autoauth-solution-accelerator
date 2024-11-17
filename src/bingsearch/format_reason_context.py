from promptflow import tool


@tool
def filter_and_transform_data(data):
    """
    Receives a list of dictionaries with a specific format and returns a list of dictionaries
    with only 'content' and 'question' keys.

    Parameters:
    data (list of dict): List of dictionaries with keys 'source', 'content', 'time_published', and 'question'.

    Returns:
    list of dict: Transformed list with dictionaries containing only 'content' and 'question'.
    """
    transformed_data = []
    for item in data:
        transformed_item = {
            "content": item.get("content"),
            "question": item.get("question"),
        }
        transformed_data.append(transformed_item)

    return transformed_data
