
import os
import re
import sys
import json
import datetime
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from pydantic import BaseModel
from src.deploy import deploy_router
from src.deployment_service import DeploymentService
from typing import Optional, List, Dict
from fastapi import Form, UploadFile, File
from langchain_together import ChatTogether
from langchain.prompts import PromptTemplate
from fastapi import APIRouter, HTTPException, Depends, FastAPI
from src.utils.create_utility_template import create_utility_template
from src.utils.create_character_template import create_character_template
from src.utils.edit_template import edit_character_template
from src.types import CharacterRequest, CharacterResponse, CharacterEditResponse

# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Configure logging
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")


character_router = APIRouter()

# Initialize Together AI client

llm = ChatTogether(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    together_api_key=TOGETHER_API_KEY,
    temperature=0.7,
    max_tokens=16000
)

def extract_json(response):
    """Extract the JSON from the response"""
    prompt = f"""RETURN only json from the below reponse, only one JSON.
    Fix keys with spacing if there are any.
    LLM Response:
    {response}
    """
    messages = [
            (
                "system",
                "You are a helpful assistant.",
            ),
            (prompt)
            ]
    ai_msg = llm.invoke(messages)               
    response = ai_msg.content
        
    match = re.search(r'```json(.*?)```', response, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        return json.loads(json_str)
    else:
        return json.loads(response)



@character_router.post("/generate_character", response_model=CharacterResponse)
async def generate_utility(request: CharacterRequest):
    """Generate a character.json based on the request"""
    # """Generate a character.json based on the request and RAG context."""
    try:
        # Retrieve relevant context from vector store
        # query = f"Find example character.json structures and patterns for a character named {request.name}"
        # result = qa_chain({"query": query})
        
        # Create generation prompt
        # prompt = create_character_template(request, result['source_documents'])
        prompt = create_utility_template(request)
        # Generate character JSON
        logger.info("Sending prompt")
        # response = llm(prompt)
        messages = [
            (
                "system",
                "You are a helpful assistant.",
            ),
            (prompt)
            ]
        ai_msg = llm.invoke(messages)               
        response = ai_msg.content
        
        
        # Parse and validate the generated JSON
        try:
            logger.info(response)
            character_json = extract_json(response)
            # with open(f"characters/{character_json['name']}_{'{date:%Y-%m-%d_%H:%M:%S}.txt'.format( date=datetime.datetime.now() )}.json", "w+") as f:
            #     json.dump(character_json, f, indent=2)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="Generated invalid JSON")
        
        # Return response with character JSON and sources
        return CharacterResponse(
            character_json=character_json,
            # reference_sources=[doc.metadata['source'] for doc in result['source_documents']]
        )
        
    except Exception as e:
        logger.error(f"Error generating character: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@character_router.post("/edit_character", response_model=CharacterEditResponse)
async def edit_character( prompt: str = Form(...),
    update_key: str = Form(...),
    character: UploadFile = File(...)):
    """Generate a character.json based on the request"""
    # """Generate a character.json based on the request and RAG context."""
    try:
        content, content_hash, json_content = await DeploymentService.process_character_file(character)
        logger.info(json_content)
        prompt = edit_character_template(json_content, update_key, prompt)
        # Generate character JSON
        logger.info("Sending prompt")
        # response = llm(prompt)
        messages = [
            (
                "system",
                "You are a helpful assistant.",
            ),
            (prompt)
            ]
        ai_msg = llm.invoke(messages)               
        response = ai_msg.content
        
        
        # Parse and validate the generated JSON
        try:
            logger.info(response)
            # edited_key_json = extract_json(response)
            # with open(f"characters/{character_json['name']}_{'{date:%Y-%m-%d_%H:%M:%S}.txt'.format( date=datetime.datetime.now() )}.json", "w+") as f:
            #     json.dump(character_json, f, indent=2)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="Generated invalid JSON")
        
        # Return response with character JSON and sources
        return CharacterEditResponse(
            update={update_key: response}        
        )
        
    except Exception as e:
        logger.error(f"Error generating character: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))