import json
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)


def extract_chat_history(chat) -> List[Dict[str, Any]]:
    """Extracts the list of messages from the chat history."""
    try:
        messages = chat.history.messages
        logging.info(f"Extracted {len(messages)} messages from chat history.")
        return messages
    except Exception as e:
        logging.error(f"Failed to extract chat history. Error: {e}")
        return []


def extract_last_evaluator_message(messages: List) -> str:
    """Extract the last message from the Evaluator from the chat history."""
    for message in reversed(messages):
        if message.role == "assistant" and message.name == "Evaluator":
            content = message.items[0].text if message.items else message.content
            logging.info(f"Found the last evaluator message: {content}")
            return content
    logging.warning("No evaluator message found in the chat history.")
    return ""


def extract_json_from_message(message_content: str) -> str:
    """Extract the JSON block from the message content."""
    try:
        if "```json" in message_content:
            message_content = message_content.replace("```json", "").replace("```", "").strip()
        logging.info(f"Extracted JSON from message: {message_content}")
        return message_content
    except Exception as e:
        logging.error(f"Failed to extract JSON from message. Error: {e}")
        return ""


def parse_json_content(message_content: str) -> Dict[str, Any]:
    """Parse the JSON from the last evaluator message content."""
    try:
        if not message_content:
            logging.warning("Message content is empty, cannot parse JSON.")
            return {}
        
        logging.info(f"Parsing message content as JSON: {message_content}")
        parsed_json = json.loads(message_content)
        logging.info(f"Parsed JSON successfully: {parsed_json}")
        return parsed_json
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}. Content: {message_content}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error while parsing JSON: {e}. Content: {message_content}")
        return {}


def extract_policies_from_parsed_json(parsed_json: Dict[str, Any]) -> List[str]:
    """Extract the list of policies from the parsed evaluator JSON."""
    if not parsed_json:
        logging.warning("Parsed JSON is empty or invalid, no policies to extract.")
        return []

    policies = parsed_json.get("policies", [])
    
    if not isinstance(policies, list):
        logging.error(f"Expected 'policies' to be a list, but got: {type(policies)}")
        return []
    
    logging.info(f"Extracted policies: {policies}")
    return policies


def get_policies_from_chat(chat) -> List[str]:
    """Full process to extract and return the policies list from the evaluator's last message."""
    messages = extract_chat_history(chat)
    last_message_content = extract_last_evaluator_message(messages)
    json_content = extract_json_from_message(last_message_content)
    parsed_json = parse_json_content(json_content)
    policies = extract_policies_from_parsed_json(parsed_json)
    return policies