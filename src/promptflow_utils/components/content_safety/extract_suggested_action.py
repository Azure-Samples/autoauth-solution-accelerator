from typing import Dict

from pipeline import tool


@tool
def my_python_tool(safety_result: Dict) -> str:
    return safety_result["suggested_action"]
