# Initial Prompt for Interaction with LLM during Development

## Crafting Effective Prompts
A well-structured prompt is essential for effective interaction with Language Learning Models (LLM) during development. The formula below serves as a guideline for creating great prompts:

`[Context] + [Specific Information] + [Intent/Goal] + [Response Format (if needed)] = Prompt`

### Example:
+ **Context**: "I’m a novice gardener"
- **Specific Information**: "Interested in growing organic vegetables in a small backyard"
+ **Intent/Goal**: "Seeking a planting guide for starting a home vegetable garden"
- **Response Format**: "Information should be presented as a concise infographic or bulleted list"

**Resulting Prompt**:
"I’m a novice gardener interested in growing organic vegetables in a small backyard. Could you suggest a planting guide for starting a home vegetable garden? Please present the information as a concise infographic or a bulleted list."

## Development Practices for Our Code

### Context
I'm a software developer working on a Python project within a large enterprise setup that is focused on AI/ML engineering.

### Specific Information
Our development practices adhere to the highest standards in the industry. These include compliance with the PEP8 style guide, utilization of automated linters for ensuring code quality, maintainability, and readability. Every function within our codebase is required to have Typing, logging (no prints allowed), error handling with try catch method and a DocString, with the latter adhering to a specific format as outlined below:

```python
def fetch_and_process_data(
        self,
        source_location: str,
        handler: Optional[DataHandler] = None,
        handler_name: Optional[str] = None,
        task_name: Optional[str] = None,
        extraction_query: Optional[str] = None,
        selected_fields: Optional[List] = None,
    ) -> ProcessedData:
        """
        Retrieve and transform data from the Specified Data Repository.

        This function fetches and processes data from a given source in the Specified Data Repository project. It allows for optional specification of a data handler, task name, extraction query, and fields to be selected.

        :param handler: The DataHandler responsible for fetching and processing the data.
        :param source_location: Path or location identifier for the data source in the repository.
        :param handler_name: (optional) Name of the data handler. If not provided, a default handler based on the project configuration will be used.
        :param task_name: (optional) Identifier for the data processing task. If not provided, it will default to the name of the data source.
        :param extraction_query: (optional) The SQL or relevant query string used to extract data from the source. If not provided, all available fields from the source will be retrieved.
        :param selected_fields: (optional) List of fields to be selected and processed from the data source. This parameter is ignored if an extraction query is provided.
        :return: The ProcessedData object containing the fetched and transformed data.
        :raises DataError: If there are issues with data retrieval or processing.
        """
```

### Intent/Goal

We aim to write high-performance code without compromising on quality. Our code is designed to be efficient, scalable, and consume minimal memory, thereby speeding up processes and delivering optimal results. Can you become my software engineer assistant following the mentioned practices ?

### Response Format

Additionally, each function we draft is accompanied by a unit test, developed using the pytest framework, ensuring adherence to the best practices outlined above. Moreover, python code doens't need to ve over commented if not specified. Take your time on your responses and let's write some code.


## **Resulting Prompt**:

I'm a software developer working on a Python project within a large enterprise setup that is focused on AI/ML engineering. Our development practices adhere to the highest standards in the industry. These include compliance with the PEP8 style guide, utilization of automated linters for ensuring code quality, maintainability, and readability. Every function within our codebase is required to have Typing, logging (no prints allowed), error handling with try catch method and a DocString, with the latter adhering to a specific format as outlined below:

```python
def fetch_and_process_data(
        self,
        source_location: str,
        handler: Optional[DataHandler] = None,
        handler_name: Optional[str] = None,
        task_name: Optional[str] = None,
        extraction_query: Optional[str] = None,
        selected_fields: Optional[List] = None,
    ) -> ProcessedData:
        """
        Retrieve and transform data from the Specified Data Repository.

        This function fetches and processes data from a given source in the Specified Data Repository project. It allows for optional specification of a data handler, task name, extraction query, and fields to be selected.

        :param handler: The DataHandler responsible for fetching and processing the data.
        :param source_location: Path or location identifier for the data source in the repository.
        :param handler_name: (optional) Name of the data handler. If not provided, a default handler based on the project configuration will be used.
        :param task_name: (optional) Identifier for the data processing task. If not provided, it will default to the name of the data source.
        :param extraction_query: (optional) The SQL or relevant query string used to extract data from the source. If not provided, all available fields from the source will be retrieved.
        :param selected_fields: (optional) List of fields to be selected and processed from the data source. This parameter is ignored if an extraction query is provided.
        :return: The ProcessedData object containing the fetched and transformed data.
        :raises DataError: If there are issues with data retrieval or processing.
        """
```

We aim to write high-performance code without compromising on quality. Our code is designed to be efficient, scalable, and consume minimal memory, thereby speeding up processes and delivering optimal results. Can you become my software engineer assistant following the mentioned practices ?

Additionally, each function we draft is accompanied by a unit test, developed using the pytest framework, ensuring adherence to the best practices outlined above. Moreover, python code doens't need to ve over commented if not specified. Take your time on your responses and let's write some code.
