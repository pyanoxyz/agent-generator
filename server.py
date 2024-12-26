from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import json
from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
# from langchain_community.llms import Together
from langchain_together import Together
from langchain_together import ChatTogether

from langchain_openai import ChatOpenAI

import logging
from dotenv import load_dotenv


load_dotenv() 
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Together AI client
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

llm = ChatTogether(
    model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
    together_api_key=TOGETHER_API_KEY,
    temperature=0.7,
    max_tokens=16000
)

MODELS_CACHE = os.getenv('MODELS_CACHE', './models')
# os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE
os.environ['HF_HOME'] = "./models"
os.makedirs(MODELS_CACHE, exist_ok=True)

# Initialize embeddings model
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
# togethercomputer/m2-bert-80M-32k-retrieval
embeddings = HuggingFaceEmbeddings(model_name="togethercomputer/m2-bert-80M-32k-retrieval",
                                   cache_folder=MODELS_CACHE,
                                   model_kwargs = {'trust_remote_code': True})


# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

class CharacterRequest(BaseModel):
    name: str
    description: str
    personality_traits: List[str]
    example_dialogues: Optional[List[Dict[str, str]]] = None

class CharacterResponse(BaseModel):
    character_json: dict
    reference_sources: List[str]


def create_character_template(character_request: CharacterRequest, context: List[str]) -> str:
    """Create a prompt template for character generation."""
    return f"""Based on the following context from the Eliza codebase and the character request, 
    create a detailed character.json file that follows the same structure and patterns:

    Context from codebase:
    {context}

    Character Request:
    Name: {character_request.name}
    Description: {character_request.description}
    Personality Traits: {', '.join(character_request.personality_traits)}
    Character uses discord client and together as model provider
    
    Generate a complete character.json that matches the structure found in the codebase but with unique
    and creative content for this new character. Include bio, lore, message examples, and style guidelines.
    The response should be valid JSON.
    only return JSON without anything else without any backtics or codeblock
    """
    
collection_name = "eliza_docs"
@app.on_event("startup")
async def startup_event():
    """Initialize the vector store and QA chain on startup."""
    global vectorstore, qa_chain
    
    # Setup vector store
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./data/chroma_db"
    )
    
    # Create QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True
    )
    
    logger.info("RAG system initialized successfully")

@app.post("/generate_character", response_model=CharacterResponse)
async def generate_character(request: CharacterRequest):
    """Generate a character.json based on the request and RAG context."""
    try:
        # Retrieve relevant context from vector store
        query = f"Find example character.json structures and patterns for a character named {request.name}"
        result = qa_chain({"query": query})
        
        # Create generation prompt
        prompt = create_character_template(request, result['source_documents'])
        
        # Generate character JSON
        logger.info("Sending prompt")
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
        
        
        # Parse and validate the generated JSON
        try:
            logger.info(response)
            character_json = json.loads(response)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="Generated invalid JSON")
        
        # Return response with character JSON and sources
        return CharacterResponse(
            character_json=character_json,
            reference_sources=[doc.metadata['source'] for doc in result['source_documents']]
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