import logging
from typing import Dict, List

from azure.search.documents._paging import SearchItemPaged
from pipeline import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool
def process_search_results_sources(result: SearchItemPaged) -> List[Dict]:
    """
    Process the results from a search query in an Azure Cognitive Search index.

    Args:
        result (SearchItemPaged): The results from a search query.

    Returns:
        List[str]: The content of each document in the search results.
    """
    sources = []
    for doc in result:
        sources.append(doc["metadata"])

    logger.info(f"sources_from_k_search: {sources}")
    return sources
