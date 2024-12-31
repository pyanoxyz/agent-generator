from fastapi import APIRouter, HTTPException, Depends
from eth_account.messages import encode_defunct
from web3 import Web3
from web3.auto import w3
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import Optional, Dict
from loguru import logger
from  datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
# Get the parent directory of the current file (src/)
current_dir = Path(__file__).parent
# Go up one level to get to the root directory where .env is
root_dir = current_dir.parent

# Load .env from the root directory
load_dotenv(root_dir / '.env')

# Initialize MongoDB client
mongodb_uri = os.getenv('MONGODB_URI')  # Replace with your MongoDB URI
client = MongoClient(mongodb_uri)
db = client.users  # Replace with your database name


class SignatureRequest(BaseModel):
    signature: str = Field(..., description="Signature is required")
    message: str = Field(..., description="Message is required")

class ClientConfig(BaseModel):
    twitter: Optional[Dict[str, str]]
    discord: Optional[Dict[str, str]]
    telegram: Optional[str]

class CharacterDataRequest(BaseModel):
    signature: str
    message: str
    character: dict
    client: ClientConfig

deploy_router = APIRouter()

def verify_signature(signature: str, message: str) -> str:
    """
    Verify an Ethereum signature and return the signer's address.
    """
    try:
        # Create the message hash
        message_hash = encode_defunct(text=message)
        
        # Recover the address from the signature
        address = w3.eth.account.recover_message(message_hash, signature=signature)
        
        return address
    except Exception as e:
        logger.error(f"Error verifying signature: {str(e)}")
        raise HTTPException(status_code=400, message="Invalid signature")

@deploy_router.post("/register")
async def register(request: SignatureRequest):
    """
    Verify a wallet signature and store the address in MongoDB.
    """
    try:
        # Verify the signature and get the address
        address = verify_signature(request.signature, request.message)
        
        # Store in MongoDB
        result = db.users.update_one(
            {"address": address},
            {"$set": {
                "address": address,
                "last_verified": datetime.utcnow()
            }},
            upsert=True
        )
        
        return {"address": address, "verified": True}
    
    except Exception as e:
        logger.error(f"Error in wallet verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@deploy_router.post("/store_character_data")
async def store_character_data(request: CharacterDataRequest):
    """
    Store character and client data associated with a wallet address.
    """
    try:
        # Verify the signature and get the address
        address = verify_signature(request.signature, request.message)
        
        # Prepare the data to store
        character_data = {
            "address": address,
            "character": request.character,
            "client_config": request.client.dict(),
            "updated_at": datetime.utcnow()
        }
        
        # Store in MongoDB
        result = db.character_data.update_one(
            {"address": address},
            {"$set": character_data},
            upsert=True
        )
        
        return {
            "address": address,
            "stored": True,
            "updated": result.modified_count > 0,
            "created": result.upserted_id is not None
        }
    
    except Exception as e:
        logger.error(f"Error storing character data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add router to your main FastAPI app
# app.include_router(router, prefix="/api/v1")nm ukhy   u89rtgiju regu iyfrehv y rfëhe3f3y         r 7yr4f3t67yr4fh7ryfê478er6y4e3ruy73e2uehy32d67ew2d3hye3wg     