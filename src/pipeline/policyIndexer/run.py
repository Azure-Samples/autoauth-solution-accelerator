import os
import yaml
import time
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    VectorSearchProfile,
    IndexProjectionMode,
    AzureOpenAIVectorizerParameters,
    AzureOpenAIVectorizer,
    SemanticConfiguration,
    SemanticPrioritizedFields,    
    SemanticField,
    SearchIndexerDataSourceConnection,
    SearchIndexerDataContainer,
    SearchIndexer,
    IndexingParameters,
    IndexingParametersConfiguration,
    BlobIndexerImageAction,
    SplitSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    AzureOpenAIEmbeddingSkill,
    OcrSkill,
    SearchIndexerSkillset,
    CognitiveServicesAccountKey,
    SemanticSearch,
    HnswParameters,
    NativeBlobSoftDeleteDeletionDetectionPolicy
)

from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import SearchIndexerStatus
from utils.ml_logging import get_logger

logger = get_logger()

import dotenv
dotenv.load_dotenv(".env")


class PolicyIndexingPipeline:
    """
    A pipeline to automate the process of indexing policy documents into Azure Cognitive Search.
    """

    def __init__(self, config_path: str = 'src\pipeline\policyIndexer\settings.yaml'):
        """
        Initialize the PolicyIndexingPipeline with configuration from a YAML file.

        Args:
            config_path (str): Path to the configuration YAML file.
        """
        # Load settings from YAML file
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        # Load environment variables
        load_dotenv(override=True)

        self.endpoint: str = os.environ["AZURE_AI_SEARCH_SERVICE_ENDPOINT"]
        search_admin_key: Optional[str] = os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
        self.credential: AzureKeyCredential = (
            AzureKeyCredential(search_admin_key) if search_admin_key else DefaultAzureCredential()
        )
        self.index_name: str = config['azure_search']['index_name']

        self.blob_connection_string: str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        self.blob_container_name: str = config['azure_search_indexer_settings']['azure_blob_storage_container_name']
        self.blob_prefix: str = config['azure_search_indexer_settings'].get('blob_prefix', '')

        self.azure_openai_endpoint: str = os.environ["AZURE_OPENAI_ENDPOINT"]
        self.azure_openai_key: str = os.getenv("AZURE_OPENAI_KEY")
        self.azure_openai_embedding_deployment: str = os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"
        )
        self.azure_openai_model_name: str = os.getenv(
            "AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large"
        )
        self.azure_openai_model_dimensions: int = int(os.getenv(
            "AZURE_OPENAI_EMBEDDING_DIMENSIONS", 3072
        ))

        self.azure_ai_services_key: str = os.getenv("AZURE_AI_SERVICES_KEY", "")
        self.use_ocr: bool = config['azure_search_indexer_settings']['use_ocr']
        self.add_page_numbers: bool = config['azure_search_indexer_settings']['add_page_numbers']

        self.indexer_name: str = config['azure_search_indexer_settings']['indexer_name']
        self.skillset_name: str = config['azure_search_indexer_settings']['skillset_name']
        self.data_source_name: str = config['azure_search_indexer_settings']['data_source_name']
        self.remote_document_path: str = config['azure_search_indexer_settings']['remote_document_path']

        self.vector_search_config: Dict[str, Any] = config['vector_search']
        self.skills_config: Dict[str, Any] = config['skills']


        self.blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
            self.blob_connection_string
        )
        self.index_client: SearchIndexClient = SearchIndexClient(
            endpoint=self.endpoint, credential=self.credential
        )
        self.indexer_client: SearchIndexerClient = SearchIndexerClient(
            endpoint=self.endpoint, credential=self.credential
        )

    def upload_documents(self, local_path: str) -> None:
        """
        Upload PDF documents from a local directory to Azure Blob Storage.

        Args:
            local_path (str): Local directory containing PDF documents.
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.blob_container_name)
            for root, dirs, files in os.walk(local_path):
                for file_name in files:
                    if file_name.lower().endswith('.pdf'):
                        file_path = os.path.join(root, file_name)
                        blob_path = os.path.join(
                            self.remote_document_path, os.path.relpath(file_path, local_path)
                        )
                        blob_client = container_client.get_blob_client(blob_path)

                        with open(file_path, 'rb') as data:
                            blob_client.upload_blob(data, overwrite=True)
                        logger.info(f"Uploaded {file_path} to {blob_path}")
        except Exception as e:
            logger.error(f"Failed to upload documents: {e}")
            raise

    def create_data_source(self) -> None:
        """
        Create or update the data source connection for the indexer.
        """
        try:
            container = SearchIndexerDataContainer(
                name=self.blob_container_name,
                query=f"'{self.blob_prefix}'" if self.blob_prefix else None
            )
            data_source_connection = SearchIndexerDataSourceConnection(
                name=self.data_source_name,
                type="azureblob",
                connection_string=self.blob_connection_string,
                container=container,
                data_deletion_detection_policy=NativeBlobSoftDeleteDeletionDetectionPolicy()
            )

            data_source = self.indexer_client.create_or_update_data_source_connection(data_source_connection)
            logger.info(f"Data source '{data_source.name}' created or updated")
        except Exception as e:
            logger.error(f"Failed to create data source: {e}")
            raise

    def create_index(self) -> None:
        """
        Create or update the search index with the specified fields and configurations.
        """
        try:
            # Define fields
            fields = [
                SearchField(
                    name="parent_id",
                    type=SearchFieldDataType.String,
                    sortable=True,
                    filterable=True,
                    facetable=True
                ),
                SearchField(
                    name="title",
                    type=SearchFieldDataType.String,
                ),
                SearchField(
                    name="parent_path",
                    type=SearchFieldDataType.String,
                ),
                SearchField(
                    name="chunk_id",
                    type=SearchFieldDataType.String,
                    key=True,
                    sortable=True,
                    filterable=True,
                    facetable=True,
                    analyzer_name="keyword"
                ),
                SearchField(
                    name="chunk",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    sortable=False,
                    filterable=False,
                    facetable=False,
                ),
                SearchField(
                    name="vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=self.azure_openai_model_dimensions,
                    vector_search_profile_name="myHnswProfile"
                )
            ]

            if self.add_page_numbers:
                fields.append(
                    SearchField(
                        name="page_number",
                        type=SearchFieldDataType.String,
                        sortable=True,
                        filterable=True,
                        facetable=False
                    )
                )

            # Configure the vector search configuration
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name=self.vector_search_config['algorithms'][0]['name'],
                        parameters=HnswParameters(
                            m=self.vector_search_config['algorithms'][0]['parameters']['m'],
                            ef_construction=self.vector_search_config['algorithms'][0]['parameters']['ef_construction'],
                            ef_search=self.vector_search_config['algorithms'][0]['parameters']['ef_search'],
                        )
                    ),
                ],
                profiles=[
                    VectorSearchProfile(
                        name=self.vector_search_config['profiles'][0]['name'],
                        algorithm_configuration_name=self.vector_search_config['profiles'][0]['algorithm_configuration_name'],
                        vectorizer_name=self.vector_search_config['profiles'][0]['vectorizer_name'],
                    )
                ],
                vectorizers=[
                    AzureOpenAIVectorizer(
                        vectorizer_name=self.vector_search_config['vectorizers'][0]['vectorizer_name'],
                        parameters=AzureOpenAIVectorizerParameters(
                            resource_url=self.azure_openai_endpoint,
                            deployment_name=self.azure_openai_embedding_deployment,
                            model_name=self.azure_openai_model_name,
                            api_key=self.azure_openai_model_dimensions,
                        ),
                    ),
                ],
            )

            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="chunk")]
                ),
            )

            semantic_search = SemanticSearch(configurations=[semantic_config])

            # Create the search index
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )

            # Create or update the index
            index_result = self.index_client.create_or_update_index(index)
            logger.info(f"Index '{index_result.name}' created or updated successfully.")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise

    def create_skillset(self) -> None:
        """
        Create or update the skillset used by the indexer to process documents.
        """
        try:
            if self.use_ocr:
                ocr_skill = OcrSkill(
                    description=self.skills_config['ocr_skill']['description'],
                    context=self.skills_config['ocr_skill']['context'],
                    line_ending=self.skills_config['ocr_skill']['line_ending'],
                    default_language_code=self.skills_config['ocr_skill']['default_language_code'],
                    should_detect_orientation=self.skills_config['ocr_skill']['should_detect_orientation'],
                    inputs=[
                        InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                        for entry in self.skills_config['ocr_skill']['inputs']
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name=entry['name'], target_name=entry['target_name'])
                        for entry in self.skills_config['ocr_skill']['outputs']
                    ]
                )
                split_skill = SplitSkill(
                    description=self.skills_config['split_skill']['description'],
                    text_split_mode=self.skills_config['split_skill']['text_split_mode'],
                    context=self.skills_config['split_skill']['context'],
                    maximum_page_length=self.skills_config['split_skill']['maximum_page_length'],
                    page_overlap_length=self.skills_config['split_skill']['page_overlap_length'],
                    inputs=[
                        InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                        for entry in self.skills_config['split_skill']['inputs']
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name=entry['name'], target_name=entry['target_name'])
                        for entry in self.skills_config['split_skill']['outputs']
                    ]
                )
                embedding_skill = AzureOpenAIEmbeddingSkill(
                    description=self.skills_config['embedding_skill']['description'],
                    context=self.skills_config['embedding_skill']['context'],
                    resource_url=self.azure_openai_endpoint,
                    deployment_name=self.azure_openai_embedding_deployment,
                    model_name=self.azure_openai_model_name,
                    dimensions=self.azure_openai_model_dimensions,
                    api_key=self.azure_openai_key,
                    inputs=[
                        InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                        for entry in self.skills_config['embedding_skill']['inputs']
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name=entry['name'], target_name=entry['target_name'])
                        for entry in self.skills_config['embedding_skill']['outputs']
                    ]
                )
                skills = [ocr_skill, split_skill, embedding_skill]
    
                cognitive_services_account = CognitiveServicesAccountKey(key=self.azure_ai_services_key)
    
                index_projections = SearchIndexerIndexProjection(
                    selectors=[
                        SearchIndexerIndexProjectionSelector(
                            target_index_name=self.skills_config['index_projections']['selectors'][0]['target_index_name'],
                            parent_key_field_name=self.skills_config['index_projections']['selectors'][0]['parent_key_field_name'],
                            source_context=self.skills_config['index_projections']['selectors'][0]['source_context'],
                            mappings=[
                                InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                                for entry in self.skills_config['index_projections']['selectors'][0]['mappings']
                            ]
                        )
                    ],
                    parameters=SearchIndexerIndexProjectionsParameters(
                        projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
                    )
                )
    
                skillset = SearchIndexerSkillset(
                    name=self.skillset_name,
                    description="Skillset to process and index documents with OCR and embeddings",
                    skills=skills,
                    index_projection=index_projections,
                    cognitive_services_account=cognitive_services_account
                )
    
            else:
                split_skill = SplitSkill(
                    description=self.skills_config['split_skill']['description'],
                    text_split_mode=self.skills_config['split_skill']['text_split_mode'],
                    context=self.skills_config['split_skill']['context'],
                    maximum_page_length=self.skills_config['split_skill']['maximum_page_length'],
                    page_overlap_length=self.skills_config['split_skill']['page_overlap_length'],
                    inputs=[
                        InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                        for entry in self.skills_config['split_skill']['inputs']
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name=entry['name'], target_name=entry['target_name'])
                        for entry in self.skills_config['split_skill']['outputs']
                    ]
                )
    
                embedding_skill = AzureOpenAIEmbeddingSkill(
                    description=self.skills_config['embedding_skill']['description'],
                    context=self.skills_config['embedding_skill']['context'],
                    resource_url=self.skills_config['embedding_skill']['resource_url'],
                    deployment_name=self.skills_config['embedding_skill']['deployment_name'],
                    model_name=self.skills_config['embedding_skill']['model_name'],
                    dimensions=self.skills_config['embedding_skill']['dimensions'],
                    api_key=self.skills_config['embedding_skill']['api_key'],
                    inputs=[
                        InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                        for entry in self.skills_config['embedding_skill']['inputs']
                    ],
                    outputs=[
                        OutputFieldMappingEntry(name=entry['name'], target_name=entry['target_name'])
                        for entry in self.skills_config['embedding_skill']['outputs']
                    ]
                )
    
                skills = [split_skill, embedding_skill]
    
                index_projections = SearchIndexerIndexProjection(
                    selectors=[
                        SearchIndexerIndexProjectionSelector(
                            target_index_name=self.skills_config['index_projections']['selectors'][0]['target_index_name'],
                            parent_key_field_name=self.skills_config['index_projections']['selectors'][0]['parent_key_field_name'],
                            source_context=self.skills_config['index_projections']['selectors'][0]['source_context'],
                            mappings=[
                                InputFieldMappingEntry(name=entry['name'], source=entry['source'])
                                for entry in self.skills_config['index_projections']['selectors'][0]['mappings']
                            ]
                        )
                    ],
                    parameters=SearchIndexerIndexProjectionsParameters(
                        projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS  
                    )
                )
    
                skillset = SearchIndexerSkillset(
                    name=self.skillset_name,
                    description="Skillset to process and index documents with embeddings",
                    skills=skills,
                    index_projection=index_projections
                )
    
            # Create or update the skillset
            self.indexer_client.create_or_update_skillset(skillset)
            logger.info(f"Skillset '{skillset.name}' created or updated")
        except Exception as e:
            logger.error(f"Failed to create skillset: {e}")
            raise

    def create_indexer(self) -> None:
        """
        Create or update the indexer that orchestrates the data flow.
        """
        try:
            if self.use_ocr:
                indexer_parameters = IndexingParameters(
                    configuration=IndexingParametersConfiguration(
                        image_action=BlobIndexerImageAction.GENERATE_NORMALIZED_IMAGES,
                        query_timeout=None
                    )
                )
            else:
                indexer_parameters = IndexingParameters(
                    configuration=IndexingParametersConfiguration(
                        parsing_mode="default",
                        indexing_storage_metadata=True
                    )
                )

            indexer = SearchIndexer(
                name=self.indexer_name,
                description="Indexer to index documents and generate embeddings",
                skillset_name=self.skillset_name,
                target_index_name=self.index_name,
                data_source_name=self.data_source_name,
                parameters=indexer_parameters
            )

            self.indexer_client.create_or_update_indexer(indexer)
            logger.info(f"Indexer '{indexer.name}' created or updated")
        except Exception as e:
            logger.error(f"Failed to create indexer: {e}")
            raise

    def run_indexer(self) -> None:
        """
        Run the indexer to start indexing documents.
        """
        try:
            # Start the indexer
            self.indexer_client.run_indexer(self.indexer_name)
            logger.info(f"Indexer '{self.indexer_name}' has been started.")
        except ResourceNotFoundError as e:
            logger.error(f"Indexer '{self.indexer_name}' was not found: {e}")
            raise
        except HttpResponseError as e:
            logger.error(f"Failed to run indexer: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    def indexing(self) -> None:
        """
        Orchestrate the entire indexing pipeline.

        Args:
            local_document_path (str): Local directory containing policy documents.
        """
        try:
            self.create_data_source()
            self.create_index()
            self.create_skillset()
            self.create_indexer()
        except Exception as e:
            logger.error(f"Indexing pipeline failed: {e}")
            raise

class IndexerRunner:
    """
    A class to handle running the indexer in Azure Cognitive Search.
    """

    def __init__(self, indexer_name: str):
        """
        Initialize the IndexerRunner with configuration from a YAML file.

        Args:
            config_path (str): Path to the configuration YAML file.
        """
        load_dotenv(override=True)

        self.endpoint: str = os.environ["AZURE_AI_SEARCH_SERVICE_ENDPOINT"]
        search_admin_key: Optional[str] = os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
        self.credential: AzureKeyCredential = (
            AzureKeyCredential(search_admin_key) if search_admin_key else DefaultAzureCredential()
        )
        self.indexer_name: str = indexer_name
        self.indexer_client: SearchIndexerClient = SearchIndexerClient(
            endpoint=self.endpoint, credential=self.credential
        )

    def run_indexer(self) -> None:
        """
        Run the indexer to start indexing documents.
        """
        try:
            self.indexer_client.run_indexer(self.indexer_name)
            logger.info(f"Indexer '{self.indexer_name}' has been started.")
        except ResourceNotFoundError as e:
            logger.error(f"Indexer '{self.indexer_name}' was not found: {e}")
            raise
        except HttpResponseError as e:
            logger.error(f"Failed to run indexer: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    def check_indexer_status(self) -> Optional[SearchIndexerStatus]:
        """
        Check the status of the indexer.

        Returns:
            SearchIndexerStatus: The current status of the indexer.
        """
        try:
            status = self.indexer_client.get_indexer_status(self.indexer_name)
            return status
        except ResourceNotFoundError as e:
            logger.error(f"Indexer '{self.indexer_name}' was not found: {e}")
            return None
        except HttpResponseError as e:
            logger.error(f"Failed to retrieve indexer status: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while checking indexer status: {e}")
            return None

    def monitor_indexer_status(self) -> None:
        """
        Periodically checks the indexer status every 10 seconds and logs the progress.
        Continues until the indexer either succeeds or fails.
        """
        self.run_indexer()

        while True:
            status = self.check_indexer_status()

            if status:
                logger.info(f"Indexer Status: {status.status}")
                logger.info(f"Last Run Time: {status.last_result.end_time}")
                logger.info(f"Execution Status: {status.last_result.status}")

                if status.status == "running":
                    if status.last_result.status == "inProgress":
                        logger.info("Indexer is still running... waiting for completion.")
                    elif status.last_result.status == "success":
                        logger.info(f"Indexer '{self.indexer_name}' completed successfully.")
                        break
                    elif status.last_result.status == "error":
                        logger.error(f"Indexer '{self.indexer_name}' encountered errors: {status.last_result.errors}")
                        break
                    else:
                        logger.warning(f"Indexer '{self.indexer_name}' has an unknown execution status: {status.last_result.status}")
                        break
                elif status.status == "success":
                    logger.info(f"Indexer '{self.indexer_name}' completed successfully.")
                    break
                elif status.status == "transientFailure":
                    logger.warning(f"Indexer '{self.indexer_name}' encountered a transient failure. Retrying automatically.")
                elif status.status == "persistentFailure":
                    logger.error(f"Indexer '{self.indexer_name}' encountered a persistent failure. Manual intervention needed.")
                    break
                elif status.status == "error":
                    logger.error(f"Indexer '{self.indexer_name}' encountered an error: {status.last_result.errors}")
                    break
                else:
                    logger.warning(f"Indexer '{self.indexer_name}' has an unknown status: {status.status}")
                    break
            else:
                logger.error("Failed to retrieve indexer status.")
                break

            time.sleep(10)