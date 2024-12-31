from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import json
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
# from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
# from langchain_community.llms import Together
from langchain_together import Together
from langchain_together import ChatTogether
from pathlib import Path

from langchain_openai import ChatOpenAI

import logging
from dotenv import load_dotenv
import re
from src.utils.create_character_template import create_character_template
from src.utils.create_environment_template import create_environment_template
import datetime
from src.deploy import deploy_router
from loguru import logger
from fastapi import Form, UploadFile, File
# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Configure logging
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

app = FastAPI()
app.include_router(deploy_router, prefix="/api/v1")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Together AI client

llm = ChatTogether(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    together_api_key=TOGETHER_API_KEY,
    temperature=0.7,
    max_tokens=16000
)

# MODELS_CACHE = os.getenv('MODELS_CACHE', './models')
# # os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE
# os.environ['HF_HOME'] = "./models"
# os.makedirs(MODELS_CACHE, exist_ok=True)

# Initialize embeddings model
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# togethercomputer/m2-bert-80M-32k-retrieval
# embeddings = HuggingFaceEmbeddings(model_name="togethercomputer/m2-bert-80M-32k-retrieval",
#                                    cache_folder=MODELS_CACHE,
#                                    model_kwargs = {'trust_remote_code': True})


# # Initialize text splitter
# text_splitter = RecursiveCharacterTextSplitter(
#     chunk_size=1000,
#     chunk_overlap=200,
#     length_function=len,
# )

class CharacterRequest(BaseModel):
    prompt: str

class EnviromentRequest(BaseModel):
    character_json: dict


class CharacterResponse(BaseModel):
    character_json: dict

class EnvironmentResponse(BaseModel):
    environment_file: str


# collection_name = "eliza_docs"
# @app.on_event("startup")
# async def startup_event():
#     """Initialize the vector store and QA chain on startup."""
#     global vectorstore, qa_chain
    
#     # Setup vector store
#     vectorstore = Chroma(
#         collection_name=collection_name,
#         embedding_function=embeddings,
#         persist_directory="./data/chroma_db"
#     )
    
#     # Create QA chain
#     qa_chain = RetrievalQA.from_chain_type(
#         llm=llm,
#         chain_type="stuff",
#         retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
#         return_source_documents=True
#     )
    
#     logger.info("RAG system initialized successfully")



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

@app.post("/generate_character", response_model=CharacterResponse)
async def generate_character(request: CharacterRequest):
    """Generate a character.json based on the request"""
    # """Generate a character.json based on the request and RAG context."""
    try:
        # Retrieve relevant context from vector store
        # query = f"Find example character.json structures and patterns for a character named {request.name}"
        # result = qa_chain({"query": query})
        
        # Create generation prompt
        # prompt = create_character_template(request, result['source_documents'])
        prompt = create_character_template(request)
        # Generate character JSON
        logger.info("Sending prompt")
        # response = llm(prompt)
        messages = [
            (
                "system",
                "You are helpful assistant.",
            ),
            (prompt)
            ]
        ai_msg = llm.invoke(messages)               
        response = ai_msg.content
        
        
        # Parse and validate the generated JSON
        try:
            logger.info(response)
            character_json = extract_json(response)
            logger.info(f"saved to {character_json['name']}.json")
            with open(f"characters/{character_json['name']}_{'{date:%Y-%m-%d_%H:%M:%S}.txt'.format( date=datetime.datetime.now() )}.json", "w+") as f:
                json.dump(character_json, f, indent=2)
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

@app.post("/generate_enviroment", response_model=EnvironmentResponse)
async def generate_enviroment(request: EnviromentRequest):
    """Generate a .env based on the request"""
    # """Generate a character.json based on the request and RAG context."""
    try:
        
        # Create generation prompt
        prompt = create_environment_template(request)
        # Generate character JSON
        logger.info("Sending prompt for enviroment request")
        # response = llm(prompt)
        messages = [
            (
                "system",
                "You are a helpful assistant.",
            ),
            (prompt),
    ]
        ai_msg = llm.invoke(messages)               
        response = ai_msg.content
        
        logger.info(response)
        
        # Return response with character JSON and sources
        return EnvironmentResponse(
            environment_file=response,
        )
        
    except Exception as e:
        logger.error(f"Error generating character: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)