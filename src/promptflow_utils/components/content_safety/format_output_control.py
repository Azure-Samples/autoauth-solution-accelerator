from pipeline import tool

GENERIC_ANSWER_OUTPUT = "LLM OUTPUT is deemed inappropriate and will be recorded. Please retry. Please contact your administrator for further assistance."
GENERIC_ANSWER_INPUT = "Your Input is deemed inappropriate and will be recorded. Please correct your language. Administrator will reach out for further assistance."


@tool
def format_output_tool(
    safety_result_input=None, safety_result_output=None, llm_answer=None
) -> str:
    if safety_result_input == "Reject":
        return GENERIC_ANSWER_INPUT
    elif safety_result_output == "Accept":
        return llm_answer
    else:
        return GENERIC_ANSWER_OUTPUT
