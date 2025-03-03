def get_container_and_blob_name_from_url(blob_url: str) -> tuple:
    """
    Retrieves the container name and the blob name from a blob URL.

    The container name is always the part of the URL before the last '/'.
    The blob name is always the part of the URL after the last '/'.

    :param blob_url: The blob URL.
    :return: A tuple containing the container name and the blob name.
    """
    # Split the URL by '/'
    parts = blob_url.split("/")

    # The container name is the second to last part
    container_name = parts[-2]

    # The blob name is the last part
    blob_name = parts[-1]

    return container_name, blob_name
