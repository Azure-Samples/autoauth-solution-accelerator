#!/usr/bin/env python
# coding: utf-8

import argparse
import os
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from dotenv import load_dotenv

from src.pipeline.policyIndexer.run import IndexerRunner, PolicyIndexingPipeline


def parse_arguments():
    """
    Parses command-line arguments.
    """
    print("Parsing command-line arguments...")
    parser = argparse.ArgumentParser(
        description="Script to change the working directory and perform indexing of policies."
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Path to the target directory. If not provided, uses the TARGET_DIRECTORY environment variable.",
        default=None,
    )
    return parser.parse_args()


def change_directory(target_directory):
    """
    Changes the current working directory to the target directory.
    """
    print(f"Attempting to change directory to: {target_directory}")
    if os.path.exists(target_directory):
        try:
            os.chdir(target_directory)
            print(f"Directory successfully changed to {os.getcwd()}")
        except Exception as e:
            print(f"Error changing directory: {e}")
            sys.exit(1)
    else:
        print(f"Directory {target_directory} does not exist. Exiting.")
        sys.exit(1)


def main():
    print("Loading environment variables from .env file...")
    load_dotenv()

    # Parse command-line arguments
    args = parse_arguments()
    target_directory = args.target or os.getenv("TARGET_DIRECTORY")

    if not target_directory:
        print(
            "Error: No target directory specified. Use the --target argument or set the TARGET_DIRECTORY environment variable."
        )
        sys.exit(1)

    # Change to the target directory
    change_directory(target_directory)

    # Instantiate the PolicyIndexingPipeline Class
    print("Initializing PolicyIndexingPipeline...")
    indexer = PolicyIndexingPipeline()

    # Upload Document to Landing Zone Blob Storage
    print("Uploading documents to the Landing Zone Blob Storage...")
    indexer.upload_documents(local_path="utils/data/cases/policies")
    print("Documents uploaded successfully.")

    # Create Data Source (Connect Blob)
    print("Creating data source for the blob storage...")
    indexer.create_data_source()
    print("Data source created successfully.")

    # Create Index
    print("Creating search index...")
    indexer.create_index()
    print("Index created successfully.")

    # Create Skillset
    print("Creating skillset for the index...")
    indexer.create_skillset()
    print("Skillset created successfully.")

    # Create Indexer
    print("Creating indexer...")
    indexer.create_indexer()
    print("Indexer created successfully.")

    # Create and Run Indexer
    print("Initializing the indexer runner...")
    indexer_runner = IndexerRunner(indexer_name="ai-policies-indexer")
    print("Monitoring indexer status...")
    indexer_runner.monitor_indexer_status()
    print("Indexing process completed successfully.")

    # Test Search
    print("Setting up SearchClient...")
    credential = AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_ADMIN_KEY"))
    index_name = os.getenv("AZURE_AI_SEARCH_INDEX_NAME", "ai-policies-index")

    search_client = SearchClient(
        endpoint=os.environ["AZURE_AI_SEARCH_SERVICE_ENDPOINT"],
        index_name=index_name,
        credential=credential,
    )
    print("SearchClient successfully configured.")

    SEARCH_QUERY = "afiniitor therapy"
    print(f"Performing search with query: '{SEARCH_QUERY}'...")

    vector_query = VectorizableTextQuery(
        text=SEARCH_QUERY, k_nearest_neighbors=5, fields="vector", weight=0.5
    )

    results = search_client.search(
        search_text=SEARCH_QUERY,
        vector_queries=[vector_query],
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name="my-semantic-config",
        query_caption=QueryCaptionType.EXTRACTIVE,
        query_answer=QueryAnswerType.EXTRACTIVE,
        top=5,
    )

    print("Search results retrieved. Displaying results:")
    for result in results:
        print("=" * 40)
        print(f"ID: {result['chunk_id']}")
        print(f"Reranker Score: {result['@search.reranker_score']}")
        print(f"Source_doc_path: {result['parent_path']}")
        content = (
            result["chunk"][:500] + "..."
            if len(result["chunk"]) > 500
            else result["chunk"]
        )
        print(f"Content: {content}")

        captions = result.get("@search.captions", [])
        if captions:
            caption = captions[0]
            if caption.highlights:
                print(f"Caption: {caption.highlights}")
            else:
                print(f"Caption: {caption.text}")
        print("=" * 40)

    print("Search operation completed successfully.")


if __name__ == "__main__":
    print("Starting script execution...")
    main()
    print("Script execution completed.")
