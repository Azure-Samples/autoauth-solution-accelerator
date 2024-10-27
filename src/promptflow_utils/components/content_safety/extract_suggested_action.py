from pipeline import tool
from typing import Dict

@tool
def my_python_tool(safety_result:Dict) -> str:
    return safety_result["suggested_action"]
