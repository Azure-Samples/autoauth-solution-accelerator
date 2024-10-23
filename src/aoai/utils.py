"""
This script contains a utility function for interacting with the Azure OpenAI API.
"""

from typing import Dict, List, Optional

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from requests import Response

from utils.ml_logging import get_logger

# Set up logger
logger = get_logger()


def extract_rate_limit_and_usage_info(response: Response) -> Dict[str, Optional[int]]:
    """
    Extracts rate limiting information from the Azure Open API response headers and usage information from the payload.

    :param response: The response object returned by a requests call.
    :return: A dictionary containing the remaining requests, remaining tokens, and usage information
            including prompt tokens, completion tokens, and total tokens.
    """
    headers = response.headers
    usage = response.json().get("usage", {})
    return {
        "remaining-requests": headers.get("x-ratelimit-remaining-requests"),
        "remaining-tokens": headers.get("x-ratelimit-remaining-tokens"),
        "prompt-tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def calculate_accuracy(total_estimated: int, total_actual: int) -> float:
    """
    Calculate the accuracy of the estimated tokens compared to the actual tokens.

    :param total_estimated: The total number of estimated tokens.
    :param total_actual: The total number of actual tokens.

    :return: The accuracy of the estimation as a percentage.
    """
    if total_actual > 0:
        accuracy = (total_estimated / total_actual) * 100
        accuracy = max(0, min(accuracy, 100))  # Ensure accuracy is between 0 and 100
    else:
        accuracy = 0
    logger.info(f"Accuracy: {accuracy}%")
    return accuracy


def display_token_results_table(results: List[Dict[str, int]]) -> None:
    """
    Display the results in a table format using pandas. Also, display the cumulative totals of estimated and actual tokens.

    :param results: The results of the analysis.
    """
    df = pd.DataFrame(results)

    # Add a new row for the cumulative totals
    df.loc["Total"] = {
        "estimated_tokens": df["estimated_tokens"].sum(),
        "actual_tokens": df["actual_tokens"].sum(),
    }

    # Format the DataFrame for better readability
    df.index.name = "Conversation"
    df.columns = ["Estimated Tokens", "Actual Tokens"]

    print(df.to_string())


def plot_token_analysis_results(
    results: List[Dict[str, int]], total_estimated: int, total_actual: int
) -> None:
    """
    Plot the estimated vs actual tokens using Seaborn and Matplotlib.

    :param results: The results of the analysis.
    :param total_estimated: The total number of estimated tokens.
    :param total_actual: The total number of actual tokens.
    """
    # Convert the results into a Pandas DataFrame
    df = pd.DataFrame(results)
    df["Conversation"] = (
        df.index + 1
    )  # Adding a conversation column for easier plotting

    # Melt the DataFrame for better compatibility with Seaborn's barplot
    df_melted = df.melt(
        id_vars=["Conversation"],
        value_vars=["estimated_tokens", "actual_tokens"],
        var_name="Type",
        value_name="Token Count",
    )

    # Calculate the accuracy
    accuracy = (total_estimated / total_actual) * 100 if total_actual > 0 else 0

    # Create the bar plot
    sns.set(style="whitegrid")
    plt.figure(figsize=(12, 8))
    ax = sns.barplot(
        x="Conversation",
        y="Token Count",
        hue="Type",
        data=df_melted,
        palette="coolwarm",
    )

    # Customize the plot
    plt.title("Estimated vs Actual Tokens by Conversation", fontsize=20)
    plt.xlabel("Conversation", fontsize=15)
    plt.ylabel("Token Count", fontsize=15)
    plt.legend(title="Token Type", title_fontsize="13", fontsize="12")

    # Increase the font size of the ticks for better readability
    ax.tick_params(labelsize=13)

    # Add a custom legend for the accuracy
    accuracy_color = "green" if accuracy >= 90 else "red"
    accuracy_patch = mpatches.Patch(
        color=accuracy_color, label=f"Accuracy: {accuracy:.2f}%"
    )
    ax.legend(
        handles=ax.legend_.legendHandles + [accuracy_patch],
        title_fontsize="13",
        fontsize="12",
    )

    # Display the plot
    plt.show()
