import logging
import os
import json
from typing import Dict, List, Union

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import RawVectorQuery
from azure.search.documents._paging import SearchItemPaged
from dotenv import load_dotenv
from pipeline import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set up Azure Cognitive Search credentials
service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
credential = AzureKeyCredential(key)


@tool
def search_k_best_results(
    index_name: str,
    search_query: str,
    search_vector: List[float],
    top: int = 5,
    query_language: str = "en-us",
) -> List[Dict[str, str]]:
    """
    Search for the k best results in an Azure Cognitive Search index.

    Args:
        index_name (str): The name of the Azure Cognitive Search index.
        search_query (str): The search query.
        search_vector (List[float]): The search vector represented as a list of floats.
        top (int, optional): The number of top results to return. Defaults to 5.
        query_language (str, optional): The language of the query. Defaults to "en-us".

    Returns:
        List[str]: The top k search results.
    """
    # Set up Azure Cognitive Search client
    search_client = SearchClient(service_endpoint, index_name, credential=credential)

    # Perform hybrid retrieval and reranking
    results = search_client.search(
        search_query,
        top=top,
        vector_queries=[
            RawVectorQuery(vector=search_vector, k=50, fields="content_vector")
        ],
        query_type="semantic",
        semantic_configuration_name="config",
        query_language=query_language,
    )

    result_dict = process_search_results(results)

    return result_dict


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