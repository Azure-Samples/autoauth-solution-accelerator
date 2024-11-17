import logging
import os
from typing import Dict, List

import requests
from dotenv import load_dotenv

from pipeline import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Endpoint for the Bing Search API
endpoint = os.getenv(
    "BING_SEARCH_API_ENDPOINT", "https://api.bing.microsoft.com/v7.0/search"
)

# Subscription key for the Bing Search API
subscription_key = os.getenv("BING_SEARCH_API_SUBSCRIPTION_KEY")


@tool
def get_search_results(
    query: str, refine_query: str, count: int = 10
) -> List[Dict[str, str]]:
    """
    Fetch the top 'count' search results from the Bing Search API.

    Args:
        query (str): The search query.
        refine_query (str): Additional parameters to refine the search query.
        count (int, optional): The number of top results to return. Defaults to 10.

    Returns:
        List[Dict[str, str]]: The top 'count' search results, each represented as a dictionary containing the source, content, and time published.
    """

    # Refining the query
    refined_query = f"{query} {refine_query}"

    # Parameters for the request
    params = {
        "q": refined_query,
        "mkt": "en-US",
        "setLang": "en-US",
        "count": count,
        "offset": 0,
        "textDecorations": False,
        "textFormat": "Raw",
        "safeSearch": "Moderate",
    }
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}

    # Initialize the list to store results
    results = []

    # Call the API
    try:
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        # Parse the JSON response
        data = response.json()

        # Extracting web page results
        web_pages = data.get("webPages", {}).get("value", [])

        # Iterate over each page and store its details in a dictionary, then add it to the list
        for page in web_pages:
            result_item = {
                "source": page.get("url"),
                "content": page.get("snippet"),
                "time_published": page.get("datePublished", "Not available"),
                "question": query,
            }
            results.append(result_item)

        return results

    except Exception as ex:
        logger.error(f"An error occurred: {ex}")
        return []
