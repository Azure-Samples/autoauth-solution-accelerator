import logging
import json
from typing import List, Dict

from azure.search.documents._paging import SearchItemPaged
from pipeline import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@tool
def process_search_results(result: SearchItemPaged) -> List[Dict[str, str]]:
    """
    Process the results from a search query in an Azure Cognitive Search index.

    Args:
        result (SearchItemPaged): The results from a search query.

    Returns:
        List[Dict[str, str]]: A list of dictionaries, where each dictionary contains the content and source of a document.
    """
    results = []
    for doc in result:
        content = doc["content"].replace("\n", " ")[:1000]
        metadata = json.loads(doc["metadata"])
        source = metadata.get("source", "")

        logger.info(
            f"score: {doc['@search.score']}, reranker: {doc['@search.reranker_score']}. {content}"
        )
        logger.info(f"source: {source}")

        results.append({
            "content": content,
            "source": source,
        })

    return results
