from typing import Annotated

from semantic_kernel.functions import kernel_function


class CustomPlugin:
    @kernel_function(
        name="get_news",
        description="Get news from the web",
    )
    def get_news_api(
        self, location: Annotated[str, "location name"]
    ) -> Annotated[str, "the output is a string"]:
        """Get news from the specified location."""
        return f"Get news from {location}."

    @kernel_function(
        name="ask_weather",
        description="Search Weather in a city",
    )
    def ask_weather_function(
        self, city: Annotated[str, "city name"]
    ) -> Annotated[str, "the output is a string"]:
        """Search Weather in a specified city."""
        return "Guangzhou’s weather is 30 celsius degree, and very hot."

    @kernel_function(
        name="ask_docs",
        description="Search Docs",
    )
    def ask_docs_function(
        self, docs: Annotated[str, "docs string"]
    ) -> Annotated[str, "the output is a string"]:
        """Search Docs."""
        return f"ask docs: {docs}"
