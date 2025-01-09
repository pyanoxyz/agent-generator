
from pydantic import BaseModel
from typing import Dict, Any

def edit_character_template(character: Dict[str, Any], update_key: str, prompt: str) -> str:
    """
        Create a prompt template for editing an existing character.json file,
        but only return the updated section(s) in JSON format (mimicking the structure of character.json).

        The user provides:
        1) existing_character_json: the current character configuration (valid JSON).
        2) edit_instructions: which field(s) to modify (e.g., lore, bio, topics, style, adjectives) 
        and how to modify them.

        The system should:
        - Parse the existing JSON.
        - Apply the requested edits exactly.
        - Output ONLY the updated sections in JSON format, preserving the structure 
        of those sections as they appear in character.json.
        - Do not include any additional commentary or the unmodified parts of the character.json.

        Example:
        If the user wants to update the "lore" field to ["New lore entry"], 
        output only:
        {
        "lore": ["New lore entry"]
        }

        Return no extra text, only the updated portion.
    """

    prompt_text = f"""
        You are a system that modifies an existing character.json configuration but ONLY outputs the updated '{update_key}' field in valid JSON format.

        Current character.json:
        {character}

        Update Key:
        {update_key}

        User instructions:
        {prompt}

        Instructions:
        1. Parse the existing character.json exactly as-is.
        2. Update ONLY the '{update_key}' field based on the user's instructions and the current chracter.json
        3. Output ONLY the updated '{update_key}' field in JSON format, preserving its structure 
        (e.g., an array if 'lore' is an array).
        4. Do not output any text besides the JSON snippet of the updated '{update_key}' field.
        5. The JSON must be valid and reflect only the changed content.

        Now produce the updated '{update_key}' field in JSON format (no extra text).
        """
    return prompt_text